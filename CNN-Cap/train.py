
import argparse
import os
import random
import shutil
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
try:
    from torch.utils.tensorboard import SummaryWriter
except ImportError:

    class SummaryWriter:  # type: ignore
        def __init__(self, *args, **kwargs):
            print("WARNING: tensorboard not available; proceeding without logging.")

        def add_scalar(self, *args, **kwargs):
            return None

        def add_histogram(self, *args, **kwargs):
            return None

        def close(self):
            return None
from tqdm import tqdm

from density_map_dataset import WindowCapDataset
from train_utils import AverageMeter

import resnet_custom

from common.tech_parser import get_conductor_layers
from common.loss_metrics import compute_all_metrics
from common.datasets import DENSITY_MAPS_DIR
from common.window_splitting import create_window_level_splits, verify_no_data_leakage

parser = argparse.ArgumentParser(description='3D CNN-Cap Training')
parser.add_argument('--lr', '--learning-rate', default=1e-4, type=float, metavar='LR', help='initial learning rate', dest='lr')
parser.add_argument('--epoch', default=100, type=int, help='number of epochs')
parser.add_argument('--seed', default=11037, type=int, help='random seed')
parser.add_argument('--batch_size', '--bs', default=64, type=int, help='batch size')
parser.add_argument('--num-workers', default=8, type=int, help='DataLoader worker count')
parser.add_argument('--logfile', default='log/log_train.txt', type=str, help='log file path')
parser.add_argument('--savename', type=str, help='checkpoint name', default='model_3d.pth')
parser.add_argument('--log', action='store_true', default=False, help='Train on log(target) instead of raw target')
parser.add_argument('--loss', default='msre', choices=['mse', 'msre'])
parser.add_argument('--resume', type=str, default=None)
parser.add_argument('--pretrained', type=str, default=None)
parser.add_argument('--model_type', type=str, choices=["resnet34", "resnet50", "resnet50_no_avgpool", "resnet18", "resnet101"], default="resnet34")
parser.add_argument('--goal', type=str, default='total', choices=['total', 'env'])
parser.add_argument('--wd', '--weight-decay', default=1e-4, type=float, metavar='W', help='weight decay (default: 1e-4)', dest='weight_decay')
parser.add_argument('--tb_logdir', type=str, default='runs/3d_cnncap', help='TensorBoard log directory')
parser.add_argument('--tech', type=str, required=True, help='Technology stack YAML file (required)')
parser.add_argument('--dataset-path', type=str, default='datasets',
                    help='Dataset directory path containing all subdirectories (default: datasets)')
parser.add_argument('--window-dir', type=str, default=None,
                    help='Directory containing window NPZ files (default: <dataset-path>/density_maps)')
parser.add_argument('--spef-dir', type=str, default=None,
                    help='Directory containing window SPEF files (default: use datasets/labels_*)')
parser.add_argument('--window-ids', type=str, nargs='*', help='Specific window IDs to use (default: all in window-dir)')
parser.add_argument('--max-windows', type=int, default=100, help='Maximum number of windows to use for quick iteration (default: 100, use 0 for all windows)')
parser.add_argument('--val-split', type=float, default=0.2, help='Fraction of samples reserved for validation')
parser.add_argument('--highlight-scale', type=float, default=1.0, help='Density boost applied to highlighted conductors')
parser.add_argument('--labels-solver', type=str, default='auto', choices=['auto', 'rwcap', 'raphael'],
                    help='Preferred SPEF solver when multiple label sources exist')
parser.add_argument('--random-seed', type=int, default=42,
                    help='Random seed for reproducible window splitting')
parser.add_argument('--debug-layer-dir', type=str, default='debug_layers',
                    help='Directory to dump first-sample density plots (empty string to disable)')
parser.add_argument('--debug-layer-count', type=int, default=8,
                    help='Number of layers to visualize per conductor in debug plots')
parser.add_argument('--debug-conductor-count', type=int, default=5,
                    help='Number of conductors to visualize in debug plots')

args = parser.parse_args()
print(args)

# Use provided tech file path directly
dataset_path = Path(args.dataset_path)
tech_file = Path(args.tech) if args.tech else None

log_path = Path(args.logfile)
if log_path.parent:
    log_path.parent.mkdir(parents=True, exist_ok=True)
logfile = open(log_path, 'w')
random.seed(args.seed)
np.random.seed(args.seed)
torch.manual_seed(args.seed)
torch.backends.cudnn.deterministic = True
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA device count: {torch.cuda.device_count()}")
    print(f"Current CUDA device: {torch.cuda.current_device()}")
    print(f"Device name: {torch.cuda.get_device_name()}")
    device = torch.device('cuda')
else:
    print("WARNING: CUDA not available, falling back to CPU")
    device = torch.device('cpu')
    torch.backends.cudnn.enabled = False

print(f"Using device: {device}")

# Force GPU if available but not selected
if torch.cuda.is_available() and device.type != 'cuda':
    print("WARNING: CUDA available but not selected, forcing to GPU")
    device = torch.device('cuda')


def get_model(typ: str, num_input_channels: int):
    """
    Get model with specified number of input channels

    Args:
        typ: Model type (resnet18, resnet34, resnet50, resnet50_no_avgpool)
        num_input_channels: Number of input channels (determined by tech file)

    Returns:
        Model instance
    """
    if typ == "resnet34":
        return resnet_custom.resnet34(num_classes=1, num_input_channels=num_input_channels)
    elif typ == "resnet50":
        return resnet_custom.resnet50(num_classes=1, num_input_channels=num_input_channels)
    elif typ == "resnet101":
        return resnet_custom.resnet101(num_classes=1, num_input_channels=num_input_channels)
    elif typ == "resnet18":
        return resnet_custom.resnet18(num_classes=1, num_input_channels=num_input_channels)
    elif typ == "resnet50_no_avgpool":
        return resnet_custom.resnet50_no_avgpool(num_classes=1, num_input_channels=num_input_channels)
    else:
        raise NotImplementedError


def compute_training_loss(predict: torch.Tensor, normalized_targets: torch.Tensor, raw_targets: torch.Tensor, *, loss_type: str, use_log: bool) -> torch.Tensor:
    """
    Compute either MSE or MSRE depending on CLI selection.

    Args:
        predict: Model output tensor (matches normalized target domain).
        normalized_targets: Targets used for training (raw or log-transformed).
        raw_targets: Original targets in femtoFarads.
        loss_type: 'mse' or 'msre'.
        use_log: Whether training is operating in log-domain.
    """
    if loss_type == "msre":
        if use_log:
            # Convert predictions back to linear domain before computing relative error.
            pred_linear = torch.exp(predict)
            target_linear = raw_targets
        else:
            pred_linear = predict
            target_linear = normalized_targets
        denom = torch.clamp(target_linear.abs(), min=1e-6)
        rel_err = (pred_linear - target_linear) / denom
        return torch.mean(rel_err * rel_err)
    # Default to standard MSE on the normalized targets.
    return torch.mean((predict - normalized_targets) ** 2)


def save_state(model, epoch, loss, args, optimizer, isbest, best_mape=None):
    dirpath = 'saved_models/'
    os.makedirs(dirpath, exist_ok=True)
    state = {
        'epoch': epoch,
        'state_dict': model.state_dict(),
        'optimizer': optimizer.state_dict(),
        'isbest': isbest,
        'loss': loss,
        'best_mape': best_mape,  # Save best MAPE for model selection
    }
    filename = args.savename
    torch.save(state, dirpath + filename)
    if isbest:
        shutil.copyfile(dirpath + filename, dirpath + 'best.' + filename)


def train(train_loader, optimizer, model, epoch, args, report_ratio):
    losses = AverageMeter()
    maxerr = 0
    errs = []

    model.train()
    for i, batch in enumerate(tqdm(train_loader, desc=f"Train Epoch {epoch}")):
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            xs, ys = batch[0], batch[1]
        else:
            raise ValueError("Expected dataset to return (features, target, meta?) tuple")
        xs = xs.to(device)
        ys = ys.to(device)
        if args.log:
            normalized_ys = torch.log(ys)
        else:
            normalized_ys = ys

        predict = model(xs)

        # Debug: Check model outputs before clamping
        if epoch == 0 and i == 0:
            print(f"Model raw output stats (first batch):")
            print(f"  Raw predict - min: {predict.min().item():.6f}, max: {predict.max().item():.6f}, mean: {predict.mean().item():.6f}")
            print(f"  Raw predict std: {predict.std().item():.6f}")
            print(f"  Zero predictions count: {(predict == 0).sum().item()}/{len(predict.flatten())}")

        # Note: Removed clamping during training to let model learn appropriate scale
        # Clamping during training can create optimization issues when targets are log-transformed

        # Debug: Check input data statistics and data shuffling
        if epoch == 0 and i == 0:
            print(f"Input data stats (Epoch {epoch}, Batch {i}):")
            print(f"  xs - min: {xs.min().item():.6f}, max: {xs.max().item():.6f}, mean: {xs.mean().item():.6f}, std: {xs.std().item():.6f}")
            print(f"  ys - min: {ys.min().item():.6f}, max: {ys.max().item():.6f}, mean: {ys.mean().item():.6f}, std: {ys.std().item():.6f}")
            print(f"  normalized_ys - min: {normalized_ys.min().item():.6f}, max: {normalized_ys.max().item():.6f}, mean: {normalized_ys.mean().item():.6f}, std: {normalized_ys.std().item():.6f}")

            # Debug: Check if any non-zero targets exist in the entire batch
            non_zero_count = (ys != 0).sum().item()
            print(f"  Non-zero targets in batch: {non_zero_count}/{len(ys.flatten())}")

            if non_zero_count > 0:
                non_zero_ys = ys[ys != 0]
                print(f"  Non-zero target range: {non_zero_ys.min().item():.6f} to {non_zero_ys.max().item():.6f}")

            # Debug: Check unique values
            unique_vals = torch.unique(ys)
            print(f"  Unique target values (first 10): {unique_vals[:10].tolist()}")

            # Debug: Test SPEF parsing directly
            from spef_tools.spef_to_simple import parse_spef_components
            test_spef = "datasets/nangate45/small/labels_rwcap/W15.spef"
            try:
                ground_caps, adjacency, unit_factor = parse_spef_components(test_spef)
                print(f"  SPEF Debug for W15:")
                print(f"    Unit factor: {unit_factor:.2e}")
                print(f"    Ground caps found: {len(ground_caps)}")
                if ground_caps:
                    sample_caps = list(ground_caps.items())[:3]
                    print(f"    Sample ground caps: {sample_caps}")
                else:
                    print(f"    No ground caps found!")
                print(f"    Coupling pairs found: {len(adjacency)}")
            except Exception as e:
                print(f"  SPEF parsing error: {e}")

            print(f"Model output stats (first batch):")
            print(f"  Predict - min: {predict.min().item():.6f}, max: {predict.max().item():.6f}, mean: {predict.mean().item():.6f}")
            print(f"  Predict std: {predict.std().item():.6f}")

        # Debug: Check data shuffling across epochs
        if i == 0:  # First batch of each epoch
            # Get sample metadata from the dataset to check shuffling
            if hasattr(train_loader.dataset, '_windows') and len(train_loader.dataset._windows) > 0:
                # This is a simplified check - in practice, accessing window IDs from batch data is complex
                print(f"Epoch {epoch} - First batch processed (check if this changes across epochs)")

        # Also add epoch-level debugging to see if shuffling is working
        if i == 0 and epoch < 3:  # First 3 epochs
            print(f"Epoch {epoch} started - processing batch {i+1}/{len(train_loader)}")
            # Print first 5 target values to check if they change across epochs
            first_5_targets = ys[:5].flatten().cpu().numpy()
            print(f"  First 5 targets in epoch {epoch}: {[f'{t:.6f}' for t in first_5_targets]}")

        # Debug: Check for NaN/Inf in predictions and targets
        if torch.isnan(predict).any() or torch.isinf(predict).any():
            print(f"WARNING: NaN/Inf detected in predictions at epoch {epoch}, batch {i}")
            print(f"Predict stats: min={predict.min().item():.6f}, max={predict.max().item():.6f}, mean={predict.mean().item():.6f}")
            continue

        if torch.isnan(normalized_ys).any() or torch.isinf(normalized_ys).any():
            print(f"WARNING: NaN/Inf detected in targets at epoch {epoch}, batch {i}")
            print(f"Target stats: min={normalized_ys.min().item():.6f}, max={normalized_ys.max().item():.6f}, mean={normalized_ys.mean().item():.6f}")
            continue

        # Select between MSE and MSRE based on CLI flag
        loss = compute_training_loss(
            predict,
            normalized_ys,
            ys,
            loss_type=args.loss,
            use_log=args.log,
        )

        # Alternative: Log-space MSE for better numerical stability
        # log_predict = torch.log1p(torch.clamp(predict, min=1e-8))
        # log_target = torch.log1p(torch.clamp(normalized_ys, min=1e-8))
        # loss = torch.mean((log_predict - log_target) ** 2)

        # Check for NaN loss
        if torch.isnan(loss) or torch.isinf(loss):
            print(f"WARNING: NaN/Inf loss at epoch {epoch}, batch {i}")
            print(f"Loss value: {loss.item()}")
            print(f"Predict range: [{predict.min().item():.6f}, {predict.max().item():.6f}]")
            print(f"Target range: [{normalized_ys.min().item():.6f}, {normalized_ys.max().item():.6f}]")
            continue

        losses.update(loss.item(), ys.size(0))
        optimizer.zero_grad()
        loss.backward()

        # Gradient clipping to prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        optimizer.step()

        if args.log:
            y_pred = torch.exp(predict)
        else:
            y_pred = predict
        err = torch.abs((y_pred - ys) / (ys + 1e-6))  # Add epsilon to prevent division by zero
        err = err.data.cpu().numpy()
        maxerr = max(maxerr, err.max())
        errs += err.tolist()

    err_array = np.array(errs)
    avgerr = float(np.mean(err_array)) if err_array.size else 0.0
    ratio_above_threshold = float(np.mean(err_array > report_ratio)) if err_array.size else 0.0
    print(
        f"Epoch {epoch} Training - Loss: {losses.avg:.6f}, Max Err: {maxerr:.4f}, "
        f"Avg Err: {avgerr:.4f}, Ratio>{report_ratio*100}%: {ratio_above_threshold:.4f}"
    )
    logfile.write('Training {} {} {} {} {}\n'.format(epoch, losses.avg, maxerr, avgerr, ratio_above_threshold))
    logfile.flush()
    return losses.avg, maxerr, avgerr, ratio_above_threshold


def test(test_loader, model, epoch, args, report_ratio):
    losses = AverageMeter()
    maxerr = 0
    errs = []
    predicts = []

    # Storage for comprehensive loss metrics
    all_predictions = []
    all_targets = []
    sample_predictions = []
    sample_targets = []

    model.eval()
    with torch.no_grad():
        for i, batch in enumerate(tqdm(test_loader, desc=f"Val Epoch {epoch}")):
            if isinstance(batch, (list, tuple)) and len(batch) >= 2:
                xs, ys = batch[0], batch[1]
            else:
                raise ValueError("Expected dataset to return (features, target, meta?) tuple")
            xs = xs.to(device)
            ys = ys.to(device)
            if args.log:
                normalized_ys = torch.log(ys)
            else:
                normalized_ys = ys

            predict = model(xs)

            # Note: Removed clamping during validation to match training behavior

            # Use requested loss metric (MSE or MSRE)
            loss = compute_training_loss(
                predict,
                normalized_ys,
                ys,
                loss_type=args.loss,
                use_log=args.log,
            )

            losses.update(loss.item(), ys.size(0))
            if args.log:
                y_pred = torch.exp(predict)
            else:
                y_pred = predict
            err = torch.abs((y_pred - ys) / (ys + 1e-6))  # Add epsilon to prevent division by zero
            err = err.cpu().numpy()
            maxerr = max(maxerr, err.max())
            errs += err.tolist()
            predicts += y_pred.cpu().numpy().tolist()

            # Store predictions and targets for comprehensive loss calculation
            all_predictions.append(y_pred.cpu())
            all_targets.append(ys.cpu())

            # Collect sample predictions for display (first 5 total)
            if len(sample_predictions) < 5:
                remaining_samples = 5 - len(sample_predictions)
                batch_preds = y_pred.cpu().numpy()[:remaining_samples]
                batch_targets = ys.cpu().numpy()[:remaining_samples]

                for pred, target in zip(batch_preds, batch_targets):
                    sample_predictions.append(pred)
                    sample_targets.append(target)
                    if len(sample_predictions) >= 5:
                        break

    err_array = np.array(errs)
    avgerr = float(np.mean(err_array)) if err_array.size else 0.0
    ratio_above_threshold = float(np.mean(err_array > report_ratio)) if err_array.size else 0.0

    # Compute comprehensive loss metrics
    all_predictions_tensor = torch.cat(all_predictions, dim=0)
    all_targets_tensor = torch.cat(all_targets, dim=0)
    comprehensive_metrics = compute_all_metrics(all_predictions_tensor, all_targets_tensor)

    print(
        f"Epoch {epoch} Validation - Loss: {losses.avg:.6f}, Max Err: {maxerr:.4f}, "
        f"Avg Err: {avgerr:.4f}, Ratio>{report_ratio*100}%: {ratio_above_threshold:.4f}"
    )
    print(f"  Comprehensive Metrics - MSE: {comprehensive_metrics['mse']:.6f}, MSRE: {comprehensive_metrics['msre']:.6f}, MARE: {comprehensive_metrics['mare']:.6f}, RMSE: {comprehensive_metrics['rmse']:.6f}")

    # Display sample predictions
    print(f"  Sample Predictions (Target → Predicted):")
    sample_errors = []
    for i, (target, pred) in enumerate(zip(sample_targets, sample_predictions)):
        # Fix NumPy deprecation warnings for array-to-scalar conversion
        if hasattr(target, 'item'):
            target_val = target.item()
        elif hasattr(target, '__iter__') and not isinstance(target, str):
            target_val = float(target[0] if len(target) > 0 else 0)
        else:
            target_val = float(target)

        if hasattr(pred, 'item'):
            pred_val = pred.item()
        elif hasattr(pred, '__iter__') and not isinstance(pred, str):
            pred_val = float(pred[0] if len(pred) > 0 else 0)
        else:
            pred_val = float(pred)
        error_pct = abs((pred_val - target_val) / (target_val + 1e-6)) * 100
        sample_errors.append(error_pct)
        print(f"    {i+1}. {target_val:.6f} → {pred_val:.6f} fF (error: {error_pct:.1f}%)")
    if sample_errors:
        print(f"    Mean relative error across samples above: {np.mean(sample_errors):.2f}%")
    print(f"    (Values in femtoFarads)")

    logfile.write('Testing {} {} {} {} {}\n'.format(epoch, losses.avg, maxerr, avgerr, ratio_above_threshold))
    logfile.write('Comprehensive {} {} {} {} {}\n'.format(epoch, comprehensive_metrics['mse'], comprehensive_metrics['msre'], comprehensive_metrics['mare'], comprehensive_metrics['rmse']))
    logfile.flush()
    return losses.avg, maxerr, avgerr, ratio_above_threshold, errs, predicts, comprehensive_metrics


# Use auto-detected tech file or fall back to argument
tech_file_to_use = tech_file if tech_file else Path(args.tech)

# Parse tech file to determine number of input channels
conductor_layers, _ = get_conductor_layers(tech_file_to_use)
num_input_channels = len(conductor_layers)
print(f"\nTech file: {tech_file_to_use}")
print(f"Conductor layers ({num_input_channels}): {conductor_layers}")

# Load data
dataset_goal = "self" if args.goal == "total" else "coupling"
report_ratio = 0.05 if args.goal == "total" else 0.1

# Derive directories from dataset path if not explicitly provided
dataset_path = Path(args.dataset_path).resolve()
window_dir_path = Path(args.window_dir).resolve() if args.window_dir is not None else dataset_path / "density_maps"
spef_dir_path = Path(args.spef_dir).resolve() if args.spef_dir is not None else None

# Handle window count limiting for quick iteration
if args.window_ids is not None:
    # User specified exact windows - validate SPEF availability and apply limit if needed
    if args.max_windows > 0:
        # Filter for SPEF availability first, then apply limit
        valid_windows = []
        for window_id in args.window_ids:
            if spef_dir_path:
                spef_path = WindowCapDataset._find_spef_in_directory_static(window_id, spef_dir_path)
                if spef_path and spef_path.exists():
                    valid_windows.append(window_id)
                else:
                    print(f"Warning: No SPEF file found for window {window_id}, skipping")
            else:
                valid_windows.append(window_id)  # No SPEF validation if no SPEF dir specified

        if len(valid_windows) > args.max_windows:
            limited_window_ids = valid_windows[:args.max_windows]
            print(f"Limiting user-specified windows from {len(args.window_ids)} to {len(limited_window_ids)} (after SPEF validation)")
        else:
            limited_window_ids = valid_windows
            if len(valid_windows) < len(args.window_ids):
                print(f"Filtered user-specified windows from {len(args.window_ids)} to {len(limited_window_ids)} (missing SPEF files)")
    else:
        limited_window_ids = args.window_ids
else:
    # Auto-discover windows with early stopping and SPEF validation
    limited_window_ids = WindowCapDataset.discover_limited_windows(window_dir_path, args.max_windows, spef_dir_path)

full_dataset = WindowCapDataset(
    window_dir=window_dir_path,
    spef_dir=spef_dir_path,
    window_ids=limited_window_ids,
    goal=dataset_goal,
    highlight_scale=args.highlight_scale,
    solver_preference=args.labels_solver,
)

dataset_layer_count = full_dataset.num_layers
print(f"\nDataset-driven layer count: {dataset_layer_count}")
print(f"Active dataset layers: {full_dataset.active_layers}")

if args.debug_layer_dir:
    debug_dir = Path(args.debug_layer_dir).resolve()
    print(f"Writing debug density plots to {debug_dir}")
    try:
        full_dataset.dump_layer_debug_visuals(
            debug_dir,
            num_conductors=max(1, args.debug_conductor_count),
            num_layers=max(1, args.debug_layer_count),
        )
    except Exception as exc:
        print(f"WARNING: Failed to generate debug density plots: {exc}")

# Debug: Analyze target distribution before splitting
print(f"\n=== Target Distribution Analysis ===")
total_samples = len(full_dataset)
if total_samples > 0:
    # Sample first 1000 targets to analyze distribution without loading everything
    sample_size = min(1000, total_samples)
    target_values = []
    zero_count = 0

    for i in range(sample_size):
        try:
            sample = full_dataset[i]
            # Dataset returns (tensor, target, meta) tuple
            if isinstance(sample, tuple) and len(sample) >= 2:
                # target is the second element in the tuple
                target_tensor = sample[1]
                # Handle if it's a tensor (should be single-element)
                if hasattr(target_tensor, 'item'):
                    target_val = target_tensor.item()
                else:
                    target_val = float(target_tensor)
            elif hasattr(sample, 'target_value'):
                target_val = float(sample.target_value)
            elif isinstance(sample, torch.Tensor):
                # If it's directly a tensor
                if sample.numel() == 1:
                    target_val = sample.item()
                else:
                    print(f"Sample {i}: Tensor with {sample.numel()} elements, expected single target value")
                    continue
            else:
                print(f"Unexpected sample type for {i}: {type(sample)}")
                continue

            target_values.append(target_val)
            if target_val == 0.0:
                zero_count += 1
        except Exception as e:
            print(f"Error accessing sample {i}: {e}")

    if target_values:
        import numpy as np
        target_array = np.array(target_values)
        print(f"Sample size: {len(target_values)}/{total_samples}")
        print(f"Zero targets: {zero_count} ({zero_count/len(target_values)*100:.1f}%)")
        print(f"Target range: {target_array.min():.6f} to {target_array.max():.6f} fF")
        print(f"Target mean: {target_array.mean():.6f} fF")
        print(f"Target std: {target_array.std():.6f} fF")
        print(f"Non-zero target range: {target_array[target_array > 0].min():.6f} to {target_array.max():.6f} fF")

        # Show histogram buckets
        print(f"Target distribution:")
        bins = [0, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1, 1.0]
        for i in range(len(bins)-1):
            count = np.sum((target_array >= bins[i]) & (target_array < bins[i+1]))
            print(f"  {bins[i]:.0e} to {bins[i+1]:.0e} fF: {count} samples")
else:
    print("No samples found in dataset!")

if len(full_dataset) < 2:
    raise RuntimeError("Not enough samples to split into train/validation sets")

# NEW: Window-level splitting to prevent data leakage
val_split = max(0.0, min(0.9, float(args.val_split)))
train_ratio = 1.0 - val_split
val_ratio = val_split
test_ratio = 0.0  # Can be configured later if needed

train_dataset, val_dataset, test_dataset = create_window_level_splits(
    full_dataset,
    train_ratio=train_ratio,
    val_ratio=val_ratio,
    test_ratio=test_ratio,
    random_seed=args.random_seed
)

# Verify no data leakage
verify_no_data_leakage(train_dataset, val_dataset, test_dataset)

trainloader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True,
                         num_workers=args.num_workers, pin_memory=True,
                         persistent_workers=True if args.num_workers > 0 else False)
valloader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False,
                       num_workers=args.num_workers, pin_memory=True,
                       persistent_workers=True if args.num_workers > 0 else False)

# Note: test_dataset is available but not used in current training loop
# You can modify the training loop to include test evaluation if needed

num_input_channels = dataset_layer_count
print(f"\nInitializing model with {num_input_channels} input channel(s) based on dataset contents.")
model = get_model(args.model_type, num_input_channels)
model = model.to(device)

optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

logfile.write('{}\n'.format(args))
logfile.flush()

best_maxerr = 1e100
best_mape = None  # Track best MAPE for model selection (lower is better)
start_epoch = 0

if args.resume is not None:
    print(f"Resuming from checkpoint: {args.resume}")
    info = torch.load(args.resume)
    checkpoint = info['state_dict']
    new_state_dict = OrderedDict()
    for k, v in checkpoint.items():
        new_state_dict[k.replace('module.', '')] = v
    model.load_state_dict(new_state_dict)
    optimizer.load_state_dict(info['optimizer'])
    start_epoch = info['epoch'] + 1
    best_maxerr = info['loss']
    best_mape = info.get('best_mape', None)  # Load MAPE if available, otherwise None

if args.pretrained is not None:
    print(f"Loading pretrained weights from: {args.pretrained}")
    info = torch.load(args.pretrained)
    checkpoint = info['state_dict']
    new_state_dict = OrderedDict()
    for k, v in checkpoint.items():
        new_state_dict[k.replace('module.', '')] = v
    model.load_state_dict(new_state_dict)

print(f"\nStarting training for {args.epoch} epochs...")
print(f"Training samples: {len(train_dataset)}, Validation samples: {len(val_dataset)}")
print(f"Goal: {args.goal}, Model: {args.model_type}, Loss: {args.loss}")
print(f"Learning rate: {args.lr}, Batch size: {args.batch_size}\n")

os.makedirs(args.tb_logdir, exist_ok=True)
writer = SummaryWriter(log_dir=args.tb_logdir)

for epoch in range(start_epoch, args.epoch):
    train_loss, train_maxerr, train_avgerr, train_ratio = train(trainloader, optimizer, model, epoch, args, report_ratio)
    val_loss, maxerr, avgerr, val_ratio, errs, preds, comprehensive_metrics = test(valloader, model, epoch, args, report_ratio)

    lr = optimizer.param_groups[0]['lr']
    writer.add_scalar('lr', lr, epoch)
    writer.add_scalar('train/loss', train_loss, epoch)
    writer.add_scalar('train/max_err', train_maxerr, epoch)
    writer.add_scalar('train/avg_err', train_avgerr, epoch)
    writer.add_scalar('train/ratio_above_threshold', train_ratio, epoch)
    writer.add_scalar('val/loss', val_loss, epoch)
    writer.add_scalar('val/max_err', maxerr, epoch)
    writer.add_scalar('val/avg_err', avgerr, epoch)
    writer.add_scalar('val/ratio_above_threshold', val_ratio, epoch)

    # Add comprehensive loss metrics to TensorBoard
    writer.add_scalar('val/mse', comprehensive_metrics['mse'], epoch)
    writer.add_scalar('val/msre', comprehensive_metrics['msre'], epoch)
    writer.add_scalar('val/mare', comprehensive_metrics['mare'], epoch)
    writer.add_scalar('val/rmse', comprehensive_metrics['rmse'], epoch)

    try:
        earr = np.array(errs).reshape(-1)
        writer.add_histogram('val/errors', earr, epoch)
    except Exception:
        pass

    # Track best model based on MAPE (lower is better) instead of max error
    current_mape = comprehensive_metrics['mare']
    if best_mape is None or current_mape < best_mape:
        best_mape = current_mape
        isbest = True
        print(f"New best model! MAPE: {current_mape:.4%} (Max error: {maxerr:.4f})")
    else:
        isbest = False

    save_state(model, epoch, maxerr, args, optimizer, isbest, best_mape)

print("\nTraining completed!")
print(f"Best MAPE achieved: {best_mape:.4%}")
print(f"Final max error: {maxerr:.4f}")
logfile.close()
writer.close()
