import torch
import torch.nn as nn
import math
import sys
from pathlib import Path
from density_map_dataset import CouplingDataset, MainDataset
import argparse
from train_utils import AverageMeter
from tqdm import tqdm
import random
import numpy as np
import os
from collections import OrderedDict
import resnet_custom

from common.tech_parser import get_conductor_layers, get_num_conductor_channels

parser = argparse.ArgumentParser(description='')
parser.add_argument('--seed', default=11037, type=int, help='random seed')
parser.add_argument('--batch_size', '--bs', default=64, type=int, help='batch size')
parser.add_argument('--logfile', default='log/log.txt', type=str, help='log file path')
parser.add_argument('--dataset-path', default='datasets', type=str, help='Dataset directory path containing all subdirectories')
    parser.add_argument('--data-path', default=None, type=str, help='Deprecated: use --dataset-path instead')
parser.add_argument('--savename', type=str, help='checkpoint name', default='demo.pth')
parser.add_argument('--filtered', action='store_true', default=False)
parser.add_argument('--filter_threshold', default=0.05, type=float)
parser.add_argument('--log', action='store_true', default=False)
parser.add_argument('--loss', default='msre', choices=['mse', 'msre'])
parser.add_argument('--pretrained', type=str, default=None)
parser.add_argument('--model_type', type=str, choices=["resnet34", "resnet50", "resnet50_no_avgpool", "resnet18"], default="resnet34")
parser.add_argument('--goal', type=str, default='total', choices=['total', 'env'])
parser.add_argument('--wd', '--weight-decay', default=1e-4, type=float, metavar='W', help='weight decay (default: 1e-4)', dest='weight_decay')
parser.add_argument('--evaluate', action='store_true', default=False, help='evaluation mode (allows overwriting logfile)')
parser.add_argument('--tech', type=str, required=True, help='Technology stack YAML file (required)')
args = parser.parse_args()
print(args)

# Handle dataset path - use new --dataset-path or fall back to old --data-path
if hasattr(args, 'dataset_path') and args.dataset_path:
    dataset_path = args.dataset_path
elif hasattr(args, 'data_path') and args.data_path:
    dataset_path = args.data_path
    print("Warning: --data-path is deprecated, use --dataset-path instead")
else:
    dataset_path = 'datasets'
if os.path.exists(args.logfile) and not args.evaluate:
    print(f"error: {args.logfile} exists, abort.")
    exit()
logfile = open(args.logfile, 'a')
random.seed(args.seed)
np.random.seed(args.seed)
torch.manual_seed(args.seed)
torch.backends.cudnn.deterministic = True


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
    elif typ == "resnet18":
        return resnet_custom.resnet18(num_classes=1, num_input_channels=num_input_channels)
    elif typ == "resnet50_no_avgpool":
        return resnet_custom.resnet50_no_avgpool(num_classes=1, num_input_channels=num_input_channels)
    else:
        raise NotImplementedError


def test(test_loader, model, epoch, args):
    losses = AverageMeter()
    maxerr = 0
    errs = []
    predicts = []
    model.eval()
    with torch.no_grad():
        for i, (xs, ys) in enumerate(tqdm(test_loader)):
            xs = xs.cuda()
            ys = ys.cuda()
            if args.log:
                normalized_ys = torch.log(ys)
            else:
                normalized_ys = ys

            predict = model(xs)
            if args.loss == 'mse':
                loss = torch.mean((predict - normalized_ys) ** 2)
            else:
                loss = torch.mean((1 - predict / normalized_ys) ** 2)

            losses.update(loss.item(), ys.size(0))
            if args.log:
                y_pred = torch.exp(predict)
            else:
                y_pred = predict
            err = torch.abs((y_pred - ys) / ys)
            err = err.cpu().numpy()
            maxerr = max(maxerr, err.max())
            errs += err.tolist()
            predicts += y_pred.cpu().numpy().tolist()
    avgerr = np.mean(errs)
    print(epoch, losses.avg, maxerr, avgerr)
    five_ratio = np.sum(np.array(errs) > report_ratio) / len(errs)
    logfile.write('Testing {} {} {} {} {}\n'.format(epoch, losses.avg, maxerr, avgerr, five_ratio))
    logfile.flush()
    return losses.avg, maxerr, avgerr, errs, predicts


# Parse tech file to determine number of input channels
conductor_layers, _ = get_conductor_layers(args.tech)
num_input_channels = len(conductor_layers)
print(f"\nTech file: {args.tech}")
print(f"Conductor layers ({num_input_channels}): {conductor_layers}")

# For label files, use layer names joined with underscore (for compatibility)
target_layers = "_".join(conductor_layers)
goal = "total" if args.goal == "total" else "env"
report_ratio = 0.05 if args.goal == "total" else 0.1

label_file_val = os.path.join(dataset_path, f"label/{target_layers}_{goal}_val.txt")
if not os.path.exists(label_file_val):
    raise FileNotFoundError(
        f"Validation label file not found: {label_file_val}\n"
        f"Expected label file format: <layer1>_<layer2>_..._{goal}_val.txt"
    )

with open(label_file_val, "r") as f:
    val_content = f.read().strip().splitlines(keepends=False)

if args.goal == "total":
    DataSetClass = MainDataset
elif args.goal == "env":
    DataSetClass = CouplingDataset

# Pass tech_file to dataset instead of target_layers string
val_dataset = DataSetClass(args.tech, val_content, dataset_path, None, filter_threshold=args.filter_threshold)
valloader = torch.utils.data.DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=8)

model = get_model(args.model_type, num_input_channels)
model = model.cuda()

logfile.write('{}\n'.format(args))
logfile.flush()

if args.pretrained is not None:
    print(f"Loading pretrained weights from: {args.pretrained}")
    info = torch.load(args.pretrained)
    checkpoint = info['state_dict']
    new_state_dict = OrderedDict()
    for k, v in checkpoint.items():
        new_state_dict[k.replace('module.', '')] = v
    model.load_state_dict(new_state_dict)

if True:
    loss, maxerr, avgerr, errs, preds = test(valloader, model, 0, args)
    f_errs = logfile
    earr = np.array(errs)
    max_err = math.ceil(np.max(earr) * 100)
    hist_dat, hist_sp = np.histogram(earr, max_err, (0, max_err / 100))
    for i in range(max_err):
        f_errs.write(f"{hist_sp[i]}\t{hist_dat[i]}\n")
    standard = report_ratio
    five = np.sum(earr > standard) / earr.shape[0]
    f_errs.write(f"error over {standard*100}% :{(1-five)*100}%\n")
    results = []
    for i, err in enumerate(errs):
        f_errs.write(f"{i}, {err[0]}, {preds[i][0]}, {val_dataset.cases[i]}\n")
        results.append((preds[i][0], val_dataset.cases[i].val))
    np.save(f"{args.logfile}.npy", np.array(results))

    try:
        ratio_above_threshold = np.sum(np.array(errs) > report_ratio) / len(errs)
    except Exception:
        ratio_above_threshold = float('nan')

    print("\n" + "=" * 60)
    print(f"Evaluation Results for {args.goal.upper()}")
    print("=" * 60)
    print(f"Model: {args.pretrained if args.pretrained is not None else 'N/A'}")
    print(f"Validation Samples: {len(errs)}")
    print(f"Max Error: {maxerr:.4f} ({maxerr*100:.2f}%)")
    print(f"Avg Error: {avgerr:.4f} ({avgerr*100:.2f}%)")
    print(f"Ratio(Err > {report_ratio*100}%): {ratio_above_threshold:.4f} ({ratio_above_threshold*100:.2f}%)")
    print("=" * 60)
