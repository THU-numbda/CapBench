"""
Inference Pipeline for GNN-Cap

Loads trained models and performs full-chip capacitance extraction.
Implements capacitance accumulation (Algorithm 2 from paper).
"""

import torch
import torch.nn.functional as F
import numpy as np
import pandas as pd
from pathlib import Path
import argparse
from typing import Dict, List, Tuple, Optional
from tqdm import tqdm
import json

import sys
sys.path.append(str(Path(__file__).parent))

import config
from models.gnncap_model import GNNCapTotal, GNNCapCoupling, create_gnncap_models
from models.attention_pool import build_attention_mask


class CapacitanceAccumulator:
    """
    Accumulate cuboid-level capacitances to net-level

    Implements Algorithm 2 from the paper
    """

    def __init__(self):
        self.net_to_idx: Dict[str, int] = {}
        self.idx_to_net: Dict[int, str] = {}
        self.capacitance_matrix: np.ndarray = None
        self.num_nets = 0

    def initialize_from_net_names(self, net_names: List[str]):
        """Initialize capacitance matrix from net names"""
        # Create mappings
        unique_nets = sorted(set(net_names))
        self.num_nets = len(unique_nets)
        self.net_to_idx = {net: idx for idx, net in enumerate(unique_nets)}
        self.idx_to_net = {idx: net for net, idx in self.net_to_idx.items()}

        # Initialize matrix
        self.capacitance_matrix = np.zeros((self.num_nets, self.num_nets), dtype=np.float64)

    def add_node_capacitances(
        self,
        node_net_names: List[str],
        node_capacitances: torch.Tensor
    ):
        """
        Add total capacitances from nodes

        Algorithm 2, lines 2-4:
        For each node vi:
            C[f(vi), f(vi)] += c_vi
        """
        node_capacitances = node_capacitances.cpu().numpy().flatten()

        for net_name, cap in zip(node_net_names, node_capacitances):
            if net_name in self.net_to_idx:
                idx = self.net_to_idx[net_name]
                self.capacitance_matrix[idx, idx] += cap

    def add_edge_capacitances(
        self,
        edge_index: torch.Tensor,
        node_net_names: List[str],
        edge_capacitances: torch.Tensor,
        edge_mask: Optional[torch.Tensor] = None,
    ):
        """
        Add coupling capacitances from edges

        Algorithm 2, lines 5-7:
        For each edge eij:
            C[g(eij)[0], g(eij)[1]] += c_eij
        """
        edge_index_np = edge_index.cpu().numpy()
        edge_capacitances_np = edge_capacitances.cpu().numpy().flatten()

        mask_np: Optional[np.ndarray] = None
        if edge_mask is not None:
            mask = edge_mask.detach().cpu().view(-1)
            if mask.shape[0] > edge_index_np.shape[1]:
                mask = mask[:edge_index_np.shape[1]]
            elif mask.shape[0] < edge_index_np.shape[1]:
                pad = torch.zeros(edge_index_np.shape[1] - mask.shape[0], dtype=mask.dtype)
                mask = torch.cat([mask, pad], dim=0)
            mask_np = mask.numpy().astype(bool)

        for edge_idx in range(edge_index_np.shape[1]):
            if mask_np is not None and not mask_np[edge_idx]:
                continue

            source_idx = edge_index_np[0, edge_idx]
            target_idx = edge_index_np[1, edge_idx]

            if source_idx > target_idx:
                continue

            source_net = node_net_names[source_idx]
            target_net = node_net_names[target_idx]

            if source_net in self.net_to_idx and target_net in self.net_to_idx:
                i = self.net_to_idx[source_net]
                j = self.net_to_idx[target_net]

                cap = edge_capacitances_np[edge_idx]

                # Add to matrix (symmetric)
                self.capacitance_matrix[i, j] += cap
                self.capacitance_matrix[j, i] += cap

    def add_net_capacitances(
        self,
        net_names: List[str],
        net_capacitances: torch.Tensor,
    ):
        """Accumulate predictions that already represent per-net totals."""
        if self.capacitance_matrix is None:
            return
        net_caps = net_capacitances.detach().view(-1).cpu().numpy()
        for net_name, cap in zip(net_names, net_caps):
            if net_name in self.net_to_idx:
                idx = self.net_to_idx[net_name]
                self.capacitance_matrix[idx, idx] += float(cap)

    def get_capacitance_matrix(self) -> pd.DataFrame:
        """Get capacitance matrix as pandas DataFrame"""
        df = pd.DataFrame(
            self.capacitance_matrix,
            index=list(self.idx_to_net.values()),
            columns=list(self.idx_to_net.values())
        )
        return df

    def save_to_csv(self, output_path: str):
        """Save capacitance matrix to CSV"""
        df = self.get_capacitance_matrix()
        df.to_csv(output_path)
        print(f"Saved capacitance matrix to {output_path}")

        # Also save in net-pair format
        output_path_pairs = output_path.replace('.csv', '_pairs.csv')
        with open(output_path_pairs, 'w') as f:
            f.write("net1,net2,capacitance\n")

            # Total capacitances (diagonal)
            for net_name in self.idx_to_net.values():
                idx = self.net_to_idx[net_name]
                total_cap = self.capacitance_matrix[idx, idx]
                if total_cap > 0:
                    f.write(f"{net_name},{net_name},{total_cap:.6e}\n")

            # Coupling capacitances (off-diagonal)
            for i, net1 in self.idx_to_net.items():
                for j, net2 in self.idx_to_net.items():
                    if i < j:  # Upper triangle only
                        coupling_cap = self.capacitance_matrix[i, j]
                        if coupling_cap > 0:
                            f.write(f"{net1},{net2},{coupling_cap:.6e}\n")

        print(f"Saved capacitance pairs to {output_path_pairs}")


class GNNCapInference:
    """Inference engine for GNN-Cap"""

    def __init__(
        self,
        total_model_path: str,
        coupling_model_path: str,
        device: str = 'cuda',
        use_fp16: bool = True,
        use_virtual_edges: bool = True,
        aggregation: str = 'none',
        aggregation_hidden_dim: int = 128,
    ):
        self.device = device
        self.use_fp16 = use_fp16
        self.aggregation = (aggregation or 'none').lower()

        # Load models
        print("Loading models...")
        total_model, coupling_model = create_gnncap_models(
            use_virtual_edges=use_virtual_edges,
            device=device,
            aggregation=self.aggregation,
            aggregation_hidden_dim=aggregation_hidden_dim,
        )

        # Load checkpoints
        total_checkpoint = torch.load(total_model_path, map_location=device, weights_only=False)
        coupling_checkpoint = torch.load(coupling_model_path, map_location=device, weights_only=False)

        total_model.load_state_dict(total_checkpoint['model_state_dict'])
        coupling_model.load_state_dict(coupling_checkpoint['model_state_dict'])

        total_model.eval()
        coupling_model.eval()

        self.total_model = total_model
        self.coupling_model = coupling_model

        print(f"Models loaded on {device}")
        if use_fp16:
            print("Using FP16 for inference (1.5× speedup)")

    def _prepare_net_metadata(self, data: torch.utils.data.Dataset) -> Tuple[Optional[torch.Tensor], int]:
        """Ensure node_net_index and num_nets exist on the data object."""
        node_net_index = getattr(data, 'node_net_index', None)
        net_names = getattr(data, 'net_names', None)

        if node_net_index is None and hasattr(data, 'node_net_names'):
            names = list(getattr(data, 'node_net_names'))
            if not net_names:
                net_names = sorted(set(names))
                data.net_names = net_names
            index_map = {name: idx for idx, name in enumerate(net_names)}
            device = data.x.device
            node_indices = torch.tensor(
                [index_map.get(name, -1) for name in names],
                dtype=torch.long,
                device=device,
            )
            data.node_net_index = node_indices
            node_net_index = node_indices
        elif node_net_index is not None:
            device = data.x.device
            if node_net_index.device != device:
                node_net_index = node_net_index.to(device)
                data.node_net_index = node_net_index

        num_nets = getattr(data, 'num_nets', None)
        if num_nets is None:
            if net_names:
                num_nets = len(net_names)
            elif node_net_index is not None and node_net_index.numel() > 0:
                valid = node_net_index[node_net_index >= 0]
                num_nets = int(valid.max().item()) + 1 if valid.numel() > 0 else 0
            else:
                num_nets = 0
            data.num_nets = num_nets

        return node_net_index, num_nets

    @torch.no_grad()
    def predict_graph(
        self,
        graph_data: torch.utils.data.Dataset
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Predict capacitances for a single graph

        Returns:
            total_caps: Total capacitances [num_nodes]
            coupling_caps: Coupling capacitances [num_edges]
        """
        # Move to device
        data = graph_data.to(self.device)

        # Extract features
        x = data.x
        edge_index = data.edge_index
        edge_attr = data.edge_attr
        edge_is_virtual = data.edge_is_virtual if hasattr(data, 'edge_is_virtual') else None
        node_net_index, num_nets = self._prepare_net_metadata(data)
        net_mask = None
        if self.aggregation != 'none':
            net_mask = build_attention_mask(node_net_index, num_nets)

        # Predict with FP16 if enabled
        if self.use_fp16 and self.device == 'cuda':
            with torch.cuda.amp.autocast():
                total_caps = self.total_model(x, edge_index, edge_attr, edge_is_virtual, net_mask)
                coupling_caps = self.coupling_model(x, edge_index, edge_attr, edge_is_virtual)
        else:
            total_caps = self.total_model(x, edge_index, edge_attr, edge_is_virtual, net_mask)
            coupling_caps = self.coupling_model(x, edge_index, edge_attr, edge_is_virtual)

        return total_caps.squeeze(), coupling_caps.squeeze()

    def extract_full_chip(
        self,
        graph_files: List[Path],
        output_path: str,
        batch_size: int = 1  # Fixed at 1 for stable processing
    ):
        """
        Extract capacitances for full chip from multiple graph chunks

        Args:
            graph_files: List of .pt graph files
            output_path: Where to save results
            batch_size: Fixed at 1 for stable processing of variable-sized graphs
        """
        print(f"\nExtracting capacitances for {len(graph_files)} chunks...")

        # Initialize accumulator
        accumulator = CapacitanceAccumulator()

        # First pass: collect all net names
        print("Collecting net names...")
        all_net_names = set()
        for graph_file in tqdm(graph_files[:10]):  # Sample first 10 to get net names
            data = torch.load(graph_file, weights_only=False)
            if hasattr(data, 'node_net_names'):
                all_net_names.update(data.node_net_names)

        accumulator.initialize_from_net_names(list(all_net_names))
        print(f"Found {accumulator.num_nets} unique nets")

        # Second pass: predict and accumulate
        print("Predicting capacitances...")
        for i, graph_file in enumerate(tqdm(graph_files)):
            try:
                # Load graph
                data = torch.load(graph_file, weights_only=False)

                # Predict
                total_caps, coupling_caps = self.predict_graph(data)
                total_caps = total_caps.view(-1)

                # Accumulate
                if hasattr(data, 'net_names') and len(data.net_names) == total_caps.numel():
                    accumulator.add_net_capacitances(data.net_names, total_caps)
                elif hasattr(data, 'node_net_names'):
                    accumulator.add_node_capacitances(data.node_net_names, total_caps)
                    accumulator.add_edge_capacitances(
                        data.edge_index,
                        data.node_net_names,
                        coupling_caps,
                        getattr(data, 'canonical_edge_mask', None),
                    )

            except Exception as e:
                print(f"Error processing {graph_file}: {e}")
                continue

        # Save results
        accumulator.save_to_csv(output_path)

        # Print statistics
        total_cap_sum = np.diag(accumulator.capacitance_matrix).sum()
        coupling_cap_sum = (accumulator.capacitance_matrix.sum() - total_cap_sum) / 2  # Off-diagonal

        print(f"\nExtraction complete!")
        print(f"Total capacitance sum: {total_cap_sum:.6e} fF")
        print(f"Coupling capacitance sum: {coupling_cap_sum:.6e} fF")


def main():
    parser = argparse.ArgumentParser(description='GNN-Cap Inference')
    parser.add_argument('--input-dir', required=True, help='Directory with graph .pt files')
    parser.add_argument('--dataset-path', default='datasets', help='Dataset directory path (used if --input-dir is not specified)')
    parser.add_argument('--total-model', required=True, help='Path to total capacitance model')
    parser.add_argument('--coupling-model', required=True, help='Path to coupling capacitance model')
    parser.add_argument('--output', required=True, help='Output CSV file path')
    # Batch size is fixed at 1 for stable inference of variable-sized graphs
    parser.add_argument('--no-fp16', action='store_true', help='Disable FP16 inference')
    parser.add_argument('--no-cuda', action='store_true', help='Disable CUDA')
    parser.add_argument('--no-virtual-edges', action='store_true', help='Disable virtual edges')
    parser.add_argument('--aggregation', choices=['none', 'mean', 'self_attention'],
                        default='self_attention',
                        help='Net aggregation method used by the total model')
    parser.add_argument('--aggregation-hidden-dim', type=int, default=128,
                        help='Hidden dimension for attention-based aggregation')

    args = parser.parse_args()

    # Device
    device = 'cuda' if torch.cuda.is_available() and not args.no_cuda else 'cpu'

    # Find graph files
    input_dir = Path(args.input_dir)
    graph_files = sorted(list(input_dir.glob("*.pt")))
    graph_files = [f for f in graph_files if not f.name.endswith('_labels.pt')]

    print(f"Found {len(graph_files)} graph files")

    # Create inference engine
    inference = GNNCapInference(
        total_model_path=args.total_model,
        coupling_model_path=args.coupling_model,
        device=device,
        use_fp16=(not args.no_fp16 and device == 'cuda'),
        use_virtual_edges=(not args.no_virtual_edges),
        aggregation=args.aggregation,
        aggregation_hidden_dim=args.aggregation_hidden_dim,
    )

    # Run extraction (batch_size fixed at 1 for stable processing)
    inference.extract_full_chip(
        graph_files=graph_files,
        output_path=args.output,
        batch_size=1
    )

    print("Done!")


if __name__ == '__main__':
    main()
