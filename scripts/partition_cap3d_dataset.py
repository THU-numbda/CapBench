#!/usr/bin/env python3
"""
CAP3D Dataset Partitioner CLI

Pre-partitions CAP3D files by subdividing large conductor blocks into smaller
cuboids. This preprocessing step moves the subdivision logic from runtime
to a one-time preprocessing operation.

Usage:
    # Auto-detect process node from dataset path
    python scripts/partition_cap3d_dataset.py --dataset-path datasets/nangate45/small

    # Manually specify process node
    python scripts/partition_cap3d_dataset.py --dataset-path datasets/my_data --process-node nangate45

    # Custom cuboid max length
    python scripts/partition_cap3d_dataset.py --dataset-path datasets/nangate45/small --cuboid-max-length 3.0

Process nodes and default cuboid_max_length values:
- asap7: 0.5 μm
- nangate45: 3.0 μm
- sky130hd: 8.0 μm
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from window_tools.cap3d_partitioner import (
    Cap3DPartitioner,
    get_partition_params_for_process_node,
    auto_detect_process_node,
    PROCESS_NODE_PARTITION_PARAMS,
    DEFAULT_CUBOID_MAX_LENGTH,
)
from common.datasets import get_dataset_subdirs

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Partition CAP3D files by subdividing large conductor blocks.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect process node from dataset path
  %(prog)s --dataset-path datasets/nangate45/small

  # Manually specify process node
  %(prog)s --dataset-path datasets/my_data --process-node nangate45

  # Custom cuboid max length
  %(prog)s --dataset-path datasets/nangate45/small --cuboid-max-length 3.0

Process nodes and default cuboid_max_length values:
  - asap7: 0.5 μm
  - nangate45: 3.0 μm
  - sky130hd: 8.0 μm
        """
    )

    parser.add_argument(
        '--dataset-path',
        type=Path,
        required=True,
        help='Path to dataset directory (e.g., datasets/nangate45/small)'
    )

    parser.add_argument(
        '--process-node',
        type=str,
        choices=list(PROCESS_NODE_PARTITION_PARAMS.keys()),
        default=None,
        help='Process node for determining cuboid_max_length. If not specified, '
             'will be auto-detected from the dataset path.'
    )

    parser.add_argument(
        '--cuboid-max-length',
        type=float,
        default=None,
        help='Override the default cuboid_max_length in μm. If not specified, '
             'uses the process-node default.'
    )

    parser.add_argument(
        '--input-dirname',
        type=str,
        default='cap3d',
        help='Name of input directory containing CAP3D files (default: cap3d)'
    )

    parser.add_argument(
        '--output-dirname',
        type=str,
        default='cap3d_split',
        help='Name of output directory for partitioned files (default: cap3d_split)'
    )

    parser.add_argument(
        '--pattern',
        type=str,
        default='*.cap3d',
        help='Glob pattern for matching CAP3D files (default: *.cap3d)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually processing'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    dataset_path = Path(args.dataset_path)

    if not dataset_path.exists():
        logger.error(f"Dataset path does not exist: {dataset_path}")
        return 1

    # Determine process node
    process_node = args.process_node
    if process_node is None:
        process_node = auto_detect_process_node(dataset_path)
        if process_node is None:
            logger.warning(
                f"Could not auto-detect process node from '{dataset_path}'. "
                f"Using default cuboid_max_length={DEFAULT_CUBOID_MAX_LENGTH}μm"
            )
        else:
            logger.info(f"Auto-detected process node: {process_node}")

    # Determine cuboid_max_length
    cuboid_max_length = args.cuboid_max_length
    if cuboid_max_length is None and process_node:
        try:
            params = get_partition_params_for_process_node(process_node)
            cuboid_max_length = params['cuboid_max_length']
            logger.info(f"Using {process_node} parameters: cuboid_max_length={cuboid_max_length}μm")
        except ValueError as e:
            logger.error(f"Error getting process node parameters: {e}")
            return 1
    elif cuboid_max_length is None:
        cuboid_max_length = DEFAULT_CUBOID_MAX_LENGTH
        logger.info(f"Using default cuboid_max_length={cuboid_max_length}μm")

    # Get input/output directories
    dataset_dirs = get_dataset_subdirs(dataset_path)
    input_dir = dataset_path / args.input_dirname
    output_dir = dataset_path / args.output_dirname

    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return 1

    # Show summary
    print("=" * 60)
    print("CAP3D Dataset Partitioner")
    print("=" * 60)
    print(f"Dataset path:         {dataset_path}")
    print(f"Process node:         {process_node or 'auto-detect failed'}")
    print(f"Cuboid max length:    {cuboid_max_length} μm")
    print(f"Input directory:      {input_dir}")
    print(f"Output directory:     {output_dir}")
    print(f"Pattern:              {args.pattern}")
    print("=" * 60)

    if args.dry_run:
        # Just show what would be done
        cap3d_files = sorted(input_dir.glob(args.pattern))
        print(f"\nWould process {len(cap3d_files)} CAP3D files:")
        for f in cap3d_files[:10]:  # Show first 10
            print(f"  - {f.name}")
        if len(cap3d_files) > 10:
            print(f"  ... and {len(cap3d_files) - 10} more")
        return 0

    # Confirm if output directory already has files
    if output_dir.exists():
        existing_files = list(output_dir.glob(args.pattern))
        if existing_files:
            logger.warning(
                f"Output directory '{output_dir}' already contains {len(existing_files)} files. "
                f"These may be overwritten."
            )
            response = input("Continue? (y/N): ")
            if response.lower() != 'y':
                logger.info("Aborted by user")
                return 1

    # Run partitioner
    print("\nStarting partition...")
    partitioner = Cap3DPartitioner(cuboid_max_length=cuboid_max_length)

    try:
        result = partitioner.partition_directory(
            input_dir=input_dir,
            output_dir=output_dir,
            pattern=args.pattern
        )

        if not result.get('success'):
            logger.error("Partitioning failed")
            return 1

        # Show results
        stats = result.get('stats', {})
        print("\n" + "=" * 60)
        print("Partitioning Complete")
        print("=" * 60)
        print(f"Files processed:      {result['files_processed']}")
        print(f"Files failed:         {result['files_failed']}")
        print(f"Blocks before:        {stats.get('blocks_before', 0)}")
        print(f"Blocks after:         {stats.get('blocks_after', 0)}")
        print(f"Blocks partitioned:   {stats.get('blocks_partitioned', 0)}")
        print(f"Sub-blocks created:   {stats.get('sub_blocks_created', 0)}")

        if result['files_failed'] > 0:
            print("\nFailed files:")
            for f in result.get('failed_files', []):
                print(f"  - {f}")

        print("=" * 60)
        print(f"\nPartitioned files saved to: {output_dir}")

        return 0

    except Exception as e:
        logger.exception(f"Error during partitioning: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
