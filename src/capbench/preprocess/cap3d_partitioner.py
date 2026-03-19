#!/usr/bin/env python3
"""
CAP3D Block Partitioner

Pre-partitions CAP3D files by subdividing large conductor blocks into smaller
cuboids before downstream conversion. This moves the subdivision logic from
runtime to a preprocessing step.

Process-specific cuboid_max_length values:
- asap7: 0.5 μm
- nangate45: 3.0 μm
- sky130hd: 8.0 μm

Usage:
    from capbench.preprocess.cap3d_partitioner import Cap3DPartitioner

    partitioner = Cap3DPartitioner(cuboid_max_length=3.0)
    partitioner.partition_file(
        input_path="datasets/nangate45/small/cap3d/window_001.cap3d",
        output_path="datasets/nangate45/small/cap3d_split/window_001.cap3d"
    )
"""

import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from copy import deepcopy

from capbench.preprocess.cap3d_parser import StreamingCap3DParser
from capbench.preprocess.cap3d_models import Block, ParsedCap3DData

logger = logging.getLogger(__name__)

# Process-specific partitioning parameters (only cuboid_max_length needed)
PROCESS_NODE_PARTITION_PARAMS: Dict[str, Dict[str, float]] = {
    'asap7': {
        'cuboid_max_length': 0.5,
    },
    'nangate45': {
        'cuboid_max_length': 3.0,
    },
    'sky130hd': {
        'cuboid_max_length': 8.0,
    },
}

DEFAULT_CUBOID_MAX_LENGTH = 2.0


class Cap3DPartitioner:
    """Partitions CAP3D files by subdividing large conductor blocks."""

    def __init__(self, cuboid_max_length: float = DEFAULT_CUBOID_MAX_LENGTH):
        """
        Initialize the partitioner.

        Args:
            cuboid_max_length: Maximum cuboid dimension in μm. Blocks exceeding
                             this in any dimension will be subdivided.
        """
        self.cuboid_max_length = cuboid_max_length
        self.stats = {
            'files_processed': 0,
            'blocks_before': 0,
            'blocks_after': 0,
            'blocks_partitioned': 0,
            'sub_blocks_created': 0,
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self.stats = {
            'files_processed': 0,
            'blocks_before': 0,
            'blocks_after': 0,
            'blocks_partitioned': 0,
            'sub_blocks_created': 0,
        }

    def _needs_subdivision(self, block: Block) -> bool:
        """
        Check if a block needs subdivision.

        Args:
            block: Block to check

        Returns:
            True if any dimension exceeds cuboid_max_length
        """
        # Get block dimensions
        x_len = abs(block.v1[0])
        y_len = abs(block.v2[1])
        z_len = abs(block.hvec[2])

        # Check if any dimension exceeds max
        return (x_len > self.cuboid_max_length or
                y_len > self.cuboid_max_length or
                z_len > self.cuboid_max_length)

    def _subdivide_block(self, block: Block, block_index: int) -> List[Block]:
        """
        Subdivide a block into smaller cuboids using grid-based subdivision.

        This algorithm extracts the subdivision logic from the legacy graph-generation
        flow and applies it as a preprocessing step.

        Args:
            block: Block to subdivide
            block_index: Index of the block for naming sub-blocks

        Returns:
            List of subdivided blocks (may be empty if no subdivision needed)
        """
        # Get block dimensions and bounds
        bp = block.base
        v1 = block.v1
        v2 = block.v2
        hvec = block.hvec

        # Calculate bounds
        x_min, x_max = min(bp[0], bp[0] + v1[0]), max(bp[0], bp[0] + v1[0])
        y_min, y_max = min(bp[1], bp[1] + v2[1]), max(bp[1], bp[1] + v2[1])
        z_min, z_max = min(bp[2], bp[2] + hvec[2]), max(bp[2], bp[2] + hvec[2])

        # Calculate lengths
        x_len = x_max - x_min
        y_len = y_max - y_min
        z_len = z_max - z_min

        # Determine subdivision counts
        x_subdiv = max(1, int(np.ceil(x_len / self.cuboid_max_length)))
        y_subdiv = max(1, int(np.ceil(y_len / self.cuboid_max_length)))
        z_subdiv = max(1, int(np.ceil(z_len / self.cuboid_max_length)))

        # If no subdivision needed, return empty list (caller should handle)
        if x_subdiv == 1 and y_subdiv == 1 and z_subdiv == 1:
            return []

        # Create subdivided blocks
        decomposed_blocks = []
        for xi in range(x_subdiv):
            for yi in range(y_subdiv):
                for zi in range(z_subdiv):
                    # Calculate sub-block bounds
                    x0 = x_min + (xi * x_len / x_subdiv)
                    x1 = x_min + ((xi + 1) * x_len / x_subdiv)
                    y0 = y_min + (yi * y_len / y_subdiv)
                    y1 = y_min + ((yi + 1) * y_len / y_subdiv)
                    z0 = z_min + (zi * z_len / z_subdiv)
                    z1 = z_min + ((zi + 1) * z_len / z_subdiv)

                    # Create new block vectors
                    new_base = (x0, y0, z0)
                    new_v1 = (x1 - x0, 0, 0)
                    new_v2 = (0, y1 - y0, 0)
                    new_hvec = (0, 0, z1 - z0)

                    # Naming: original_block_sub_index_xiyizi
                    sub_block = Block(
                        name=f"{block.name}_sub{block_index}_{xi}{yi}{zi}",
                        parent_name=block.parent_name,
                        base=new_base,
                        v1=new_v1,
                        v2=new_v2,
                        hvec=new_hvec,
                        type=block.type,
                        layer=block.layer,
                        diel=block.diel,
                    )
                    decomposed_blocks.append(sub_block)

        return decomposed_blocks

    def partition_cap3d_data(self, parsed_data: ParsedCap3DData) -> ParsedCap3DData:
        """
        Partition all blocks in parsed CAP3D data.

        Only conductor blocks are partitioned; dielectric (medium) blocks are
        left unchanged. Ground conductor detection is NOT performed here since
        ground will be filtered out during graph generation.

        Args:
            parsed_data: Parsed CAP3D data to partition

        Returns:
            New ParsedCap3DData with partitioned blocks
        """
        # Track statistics
        blocks_before = 0
        blocks_after = 0
        partitioned_count = 0
        sub_blocks_created = 0

        # Process blocks in original order, only subdividing conductors
        new_blocks = []
        conductor_index = 0
        for block in parsed_data.blocks:
            if block.type == 'conductor':
                blocks_before += 1
                if self._needs_subdivision(block):
                    sub_blocks = self._subdivide_block(block, conductor_index)
                    if sub_blocks:
                        new_blocks.extend(sub_blocks)
                        blocks_after += len(sub_blocks)
                        partitioned_count += 1
                        sub_blocks_created += len(sub_blocks)
                        logger.debug(
                            f"Partitioned block '{block.name}' (net: {block.parent_name}) "
                            f"into {len(sub_blocks)} sub-blocks"
                        )
                    else:
                        # Shouldn't happen if _needs_subdivision returned True
                        new_blocks.append(block)
                        blocks_after += 1
                else:
                    new_blocks.append(block)
                    blocks_after += 1
                conductor_index += 1
            else:
                new_blocks.append(block)

        # Create new ParsedCap3DData with partitioned blocks
        # All other metadata (layers, plate_mediums, window, task) remains unchanged
        result = ParsedCap3DData(
            blocks=new_blocks,
            poly_elements=parsed_data.poly_elements,
            layers=parsed_data.layers,
            plate_mediums=parsed_data.plate_mediums,
            window=parsed_data.window,
            task=parsed_data.task,
            stats=deepcopy(parsed_data.stats) if parsed_data.stats else {},
        )

        # Update statistics
        self.stats['blocks_before'] += blocks_before
        self.stats['blocks_after'] += blocks_after
        self.stats['blocks_partitioned'] += partitioned_count
        self.stats['sub_blocks_created'] += sub_blocks_created
        self.stats['files_processed'] += 1

        # Update stats in the result
        if result.stats:
            result.stats['total_blocks'] = len(result.blocks)
            result.stats['conductors'] = blocks_after
            result.stats['original_conductors'] = blocks_before
            result.stats['partitioned_blocks'] = partitioned_count

        logger.info(
            f"Partitioned CAP3D data: {blocks_before} conductor blocks -> "
            f"{blocks_after} blocks ({partitioned_count} partitioned, "
            f"{sub_blocks_created} sub-blocks created)"
        )

        return result

    def partition_file(self, input_path: Path, output_path: Path) -> bool:
        """
        Partition a single CAP3D file and write the result.

        Args:
            input_path: Path to input CAP3D file
            output_path: Path to output partitioned CAP3D file

        Returns:
            True if successful, False otherwise
        """
        # Import here to avoid circular dependency
        from capbench.preprocess.cap3d_writer import write_parsed_cap3d

        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            return False

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Parse input file
            logger.info(f"Parsing CAP3D file: {input_path}")
            parser = StreamingCap3DParser(str(input_path))
            parsed_data = parser.parse_complete()

            if not parsed_data:
                logger.error(f"Failed to parse CAP3D file: {input_path}")
                return False

            # Partition blocks
            logger.info(f"Partitioning blocks with cuboid_max_length={self.cuboid_max_length}μm")
            partitioned_data = self.partition_cap3d_data(parsed_data)

            # Write output file
            logger.info(f"Writing partitioned CAP3D file: {output_path}")
            write_parsed_cap3d(str(output_path), partitioned_data)

            logger.info(f"Successfully partitioned {input_path} -> {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error partitioning {input_path}: {e}")
            return False

    def partition_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        pattern: str = "*.cap3d"
    ) -> Dict[str, any]:
        """
        Partition all CAP3D files in a directory.

        Args:
            input_dir: Input directory containing CAP3D files
            output_dir: Output directory for partitioned files
            pattern: Glob pattern for matching files (default: *.cap3d)

        Returns:
            Dictionary with processing statistics
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        if not input_dir.exists():
            logger.error(f"Input directory not found: {input_dir}")
            return {'success': False, 'error': 'Input directory not found'}

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all CAP3D files
        cap3d_files = sorted(input_dir.glob(pattern))
        if not cap3d_files:
            logger.warning(f"No CAP3D files found in {input_dir} with pattern '{pattern}'")
            return {'success': True, 'files_processed': 0, 'files_failed': 0}

        logger.info(f"Found {len(cap3d_files)} CAP3D files to process")

        # Reset stats for batch processing
        self.reset_stats()

        # Process each file
        success_count = 0
        failed_files = []

        for cap3d_file in cap3d_files:
            output_file = output_dir / cap3d_file.name
            if self.partition_file(cap3d_file, output_file):
                success_count += 1
            else:
                failed_files.append(str(cap3d_file))

        return {
            'success': True,
            'files_processed': success_count,
            'files_failed': len(failed_files),
            'failed_files': failed_files,
            'stats': deepcopy(self.stats),
        }


def get_partition_params_for_process_node(process_node: str) -> Dict[str, float]:
    """
    Get partitioning parameters for a specific process node.

    Args:
        process_node: Process node name (e.g., 'nangate45', 'asap7', 'sky130hd')

    Returns:
        Dictionary with partitioning parameters (at minimum 'cuboid_max_length')

    Raises:
        ValueError: If process node is not recognized
    """
    process_node = process_node.lower()
    if process_node not in PROCESS_NODE_PARTITION_PARAMS:
        raise ValueError(
            f"Unknown process node '{process_node}'. "
            f"Valid options: {list(PROCESS_NODE_PARTITION_PARAMS.keys())}"
        )
    return PROCESS_NODE_PARTITION_PARAMS[process_node].copy()


def auto_detect_process_node(dataset_path: Path) -> Optional[str]:
    """
    Auto-detect process node from dataset path.

    Args:
        dataset_path: Path to dataset directory

    Returns:
        Process node name if detected, None otherwise
    """
    from capbench._internal.common.datasets import extract_process_node_from_path

    try:
        return extract_process_node_from_path(dataset_path)
    except ValueError:
        return None
