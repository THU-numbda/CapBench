#!/usr/bin/env python3
"""
Generate black-box verilog (.bb.v) files from existing fakeram .v files
"""

import os
import re
import sys
from pathlib import Path

def create_black_box(input_file, output_file=None):
    """
    Create a black-box verilog file from an existing fakeram verilog file

    Args:
        input_file (str): Path to the input .v file
        output_file (str, optional): Path to output .bb.v file. If None, uses input_file with .bb.v extension
    """

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: Input file {input_file} does not exist")
        return False

    if output_file is None:
        output_path = input_path.with_suffix('.bb.v')
    else:
        output_path = Path(output_file)

    try:
        with open(input_path, 'r') as f:
            content = f.read()

        # Extract module name and parameters
        module_match = re.search(r'module\s+(\w+)\s*\(', content)
        if not module_match:
            print(f"Error: Could not find module declaration in {input_file}")
            return False

        module_name = module_match.group(1)

        # Extract the module declaration (including ports)
        module_decl_match = re.search(r'module\s+{}\s*\([^)]*\);'.format(module_name), content, re.DOTALL)
        if not module_decl_match:
            print(f"Error: Could not find complete module declaration in {input_file}")
            return False

        module_declaration = module_decl_match.group(0)

        # Extract port declarations (inputs, outputs, regs, etc.)
        port_declarations = []

        # Find all input/output declarations
        port_patterns = [
            r'input\s+(?:\[[^\]]+\]\s+)?(\w+)',
            r'output\s+(?:reg\s+)?(?:\[[^\]]+\]\s+)?(\w+)',
            r'output\s+reg\s+(?:\[[^\]]+\]\s+)?(\w+)'
        ]

        for pattern in port_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Find the full declaration line
                full_match = re.search(r'(input|output\s+(?:reg\s+))\s*(?:\[[^\]]+\]\s+)?' + re.escape(match) + r'\s*[,;]', content)
                if full_match:
                    decl = full_match.group(0).rstrip(',;')
                    if decl not in port_declarations:
                        port_declarations.append(decl)

        # Extract parameters (if any)
        parameters = []
        param_matches = re.findall(r'parameter\s+(\w+)\s*=\s*([^;]+);', content)
        for param_name, param_value in param_matches:
            parameters.append(f"   parameter {param_name} = {param_value.strip()};")

        # Create black box content
        bb_content = f"{module_declaration}\n"

        # Add parameters first (like the working example)
        if parameters:
            bb_content += "\n".join(parameters) + "\n\n"
        else:
            bb_content += "\n"

        # Add port declarations (outputs first, then inputs like the working example)
        if port_declarations:
            # Order: output regs first, then inputs
            outputs = []
            inputs = []

            for decl in port_declarations:
                if decl.startswith('output'):
                    outputs.append(decl)
                elif decl.startswith('input'):
                    inputs.append(decl)

            ordered_ports = outputs + inputs
            bb_content += "\n".join(f"   {decl};" for decl in ordered_ports) + "\n\n"
        else:
            bb_content += "\n"

        # Remove all internal logic and just keep empty module body
        bb_content += "endmodule\n"

        # Write to output file
        with open(output_path, 'w') as f:
            f.write(bb_content)

        print(f"Generated: {output_path}")
        return True

    except Exception as e:
        print(f"Error processing {input_file}: {e}")
        return False

def process_directory(directory_path, recursive=False):
    """
    Process all .v files in a directory and generate .bb.v files

    Args:
        directory_path (str): Path to directory containing .v files
        recursive (bool): Whether to process subdirectories recursively
    """

    dir_path = Path(directory_path)
    if not dir_path.exists():
        print(f"Error: Directory {directory_path} does not exist")
        return

    if recursive:
        v_files = list(dir_path.rglob("*.v"))
    else:
        v_files = list(dir_path.glob("*.v"))

    # Skip files that are already .bb.v
    v_files = [f for f in v_files if not f.name.endswith('.bb.v')]

    if not v_files:
        print("No .v files found")
        return

    success_count = 0
    for v_file in v_files:
        if create_black_box(v_file):
            success_count += 1

    print(f"\nSuccessfully generated {success_count}/{len(v_files)} black box files")

def main():
    """Main function to handle command line arguments"""

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Generate bb.v for single file:")
        print(f"    python3 {sys.argv[0]} <input_file.v> [output_file.bb.v]")
        print()
        print("  Generate bb.v for all files in directory:")
        print(f"    python3 {sys.argv[0]} <directory_path> [--recursive]")
        print()
        print("Examples:")
        print(f"    python3 {sys.argv[0]} fakeram_128x4096/fakeram_128x4096.v")
        print(f"    python3 {sys.argv[0]} fakeram_45/")
        print(f"    python3 {sys.argv[0]} . --recursive")
        sys.exit(1)

    input_path = sys.argv[1]

    if os.path.isfile(input_path):
        # Single file
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        create_black_box(input_path, output_file)

    elif os.path.isdir(input_path):
        # Directory
        recursive = len(sys.argv) > 2 and sys.argv[2] == "--recursive"
        process_directory(input_path, recursive)

    else:
        print(f"Error: {input_path} is not a valid file or directory")
        sys.exit(1)

if __name__ == "__main__":
    main()