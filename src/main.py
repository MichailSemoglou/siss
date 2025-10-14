#!/usr/bin/env python3
"""
Video effects CLI tool for applying duotone and halftone effects to videos.
"""
import argparse
import sys
import os
from duotone import apply_duotone
from halftone import apply_halftone
from utils.video_processing import get_codec_for_file


def validate_file_path(file_path, check_exists=True):
    """
    Validate file path.
    
    Args:
        file_path (str): Path to validate
        check_exists (bool): Whether to check if file exists
        
    Returns:
        str: Valid file path
        
    Raises:
        FileNotFoundError: If check_exists is True and file does not exist
        ValueError: If file path is invalid
    """
    if not file_path:
        raise ValueError("File path cannot be empty")
        
    if check_exists and not os.path.isfile(file_path):
        raise FileNotFoundError(f"File does not exist: {file_path}")
        
    return file_path


def validate_rgb_color(color):
    """
    Validate RGB color values.
    
    Args:
        color (list): RGB color values
        
    Returns:
        tuple: Valid RGB color tuple
        
    Raises:
        ValueError: If any color component is outside 0-255 range
    """
    if not all(0 <= c <= 255 for c in color):
        raise ValueError("RGB color values must be between 0 and 255")
        
    return tuple(color)


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Apply duotone and halftone effects to a video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "input", 
        help="Path to the input video"
    )
    
    parser.add_argument(
        "output", 
        help="Path to save the output video"
    )
    
    parser.add_argument(
        "--effect", 
        type=str, 
        choices=["duotone", "halftone"], 
        required=True,
        help="Effect to apply to the video (duotone or halftone)"
    )
    
    parser.add_argument(
        "--color1", 
        nargs=3, 
        type=int, 
        default=[255, 0, 0], 
        metavar=("R", "G", "B"),
        help="First color in RGB format (for symbols in halftone or dark areas in duotone)"
    )
    
    parser.add_argument(
        "--color2", 
        nargs=3, 
        type=int, 
        default=[0, 255, 255], 
        metavar=("R", "G", "B"),
        help="Second color in RGB format (for background in halftone or light areas in duotone)"
    )
    
    parser.add_argument(
        "--symbol_size", 
        type=int, 
        default=10, 
        help="Size of the largest symbol in the halftone effect"
    )
    
    parser.add_argument(
        "--symbol_type", 
        type=str, 
        choices=["plus", "asterisk", "slash"], 
        default="plus",
        help="Symbol type for halftone effect"
    )
    
    # Add codec override options
    parser.add_argument(
        "--use-codec-fix", 
        action="store_true", 
        help="Use the codec compatibility fix for different platforms"
    )
    
    return parser.parse_args()


def main():
    """Main function to process command line arguments and apply video effects."""
    try:
        args = parse_arguments()
        
        # Validate input and output paths
        input_path = validate_file_path(args.input, check_exists=True)
        output_dir = os.path.dirname(args.output)
        
        # Create output directory if it doesn't exist
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Validate colors
        color1_rgb = validate_rgb_color(args.color1)
        color2_rgb = validate_rgb_color(args.color2)
        
        # Apply selected effect
        if args.effect == "duotone":
            apply_duotone(
                input_path, 
                args.output, 
                color1_rgb, 
                color2_rgb,
                use_codec_fix=args.use_codec_fix
            )
        elif args.effect == "halftone":
            apply_halftone(
                input_path, 
                args.output, 
                args.symbol_size, 
                color1_rgb, 
                color2_rgb, 
                symbol_type=args.symbol_type,
                use_codec_fix=args.use_codec_fix
            )
            
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
