"""
Utility functions for video processing operations.

This module provides helper functions for common video operations like
loading videos, extracting frames, and saving processed results.
"""
import cv2
import numpy as np
import os
from tqdm import tqdm


def get_codec_for_file(output_path):
    """
    Determine the appropriate codec based on the file extension.
    
    Args:
        output_path (str): Path where the video will be saved
        
    Returns:
        str: Four character codec code
    """
    # Get file extension (lowercase)
    _, ext = os.path.splitext(output_path)
    ext = ext.lower()
    
    # Map extensions to codecs
    codec_map = {
        '.avi': 'XVID',
        '.mp4': 'mp4v',  # H.264 codec
        '.mov': 'mp4v',  # H.264 codec for MOV container
        '.mkv': 'X264',
        '.wmv': 'WMV2',
    }
    
    # Default to mp4v if extension not found
    return codec_map.get(ext, 'mp4v')


def load_video(video_path):
    """
    Load a video file and return a VideoCapture object.
    
    Args:
        video_path (str): Path to the video file
        
    Returns:
        cv2.VideoCapture: OpenCV VideoCapture object
        
    Raises:
        FileNotFoundError: If the video file cannot be opened
    """
    video_capture = cv2.VideoCapture(video_path)
    if not video_capture.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {video_path}")
    return video_capture


def get_video_properties(video_capture):
    """
    Get properties of a video.
    
    Args:
        video_capture (cv2.VideoCapture): OpenCV VideoCapture object
        
    Returns:
        dict: Dictionary with video properties (fps, width, height, frame_count)
    """
    properties = {
        'fps': video_capture.get(cv2.CAP_PROP_FPS),
        'width': int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'frame_count': int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
    }
    return properties


def extract_frames(video_capture, show_progress=True):
    """
    Extract all frames from a video.
    
    Args:
        video_capture (cv2.VideoCapture): OpenCV VideoCapture object
        show_progress (bool): Whether to show a progress bar
        
    Returns:
        list: List of frames as numpy arrays
    """
    frames = []
    
    # Get frame count for progress bar
    frame_count = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Create progress bar if requested
    if show_progress:
        progress_bar = tqdm(total=frame_count, desc="Extracting frames")
    
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        frames.append(frame)
        
        # Update progress bar
        if show_progress:
            progress_bar.update(1)
    
    # Close progress bar
    if show_progress:
        progress_bar.close()
        
    return frames


def save_video(output_path, frames, fps, show_progress=True):
    """
    Save a list of frames as a video file.
    
    Args:
        output_path (str): Path where the video will be saved
        frames (list): List of frames as numpy arrays
        fps (float): Frames per second for the output video
        show_progress (bool): Whether to show a progress bar
        
    Raises:
        ValueError: If no frames are provided
    """
    if not frames:
        raise ValueError("No frames to save.")
    
    height, width, _ = frames[0].shape
    codec = get_codec_for_file(output_path)
    fourcc = cv2.VideoWriter_fourcc(*codec)
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Create progress bar if requested
    if show_progress:
        progress_bar = tqdm(total=len(frames), desc="Saving video")
    
    for frame in frames:
        video_writer.write(frame)
        
        # Update progress bar
        if show_progress:
            progress_bar.update(1)
    
    # Close progress bar
    if show_progress:
        progress_bar.close()
        
    video_writer.release()
    print(f"Video saved to {output_path}")


def process_video_frames(video_path, output_path, process_function, **kwargs):
    """
    Process a video by applying a function to each frame.
    
    Args:
        video_path (str): Path to the input video
        output_path (str): Path where processed video will be saved
        process_function (callable): Function to apply to each frame
            The function should take a frame and return a processed frame
        **kwargs: Additional arguments to pass to the process_function
        
    Example:
        def grayscale(frame):
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
        process_video_frames('input.mp4', 'output.mp4', grayscale)
    """
    # Load video
    cap = load_video(video_path)
    
    try:
        # Get video properties
        props = get_video_properties(cap)
        
        # Create output video writer with appropriate codec
        codec = get_codec_for_file(output_path)
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, props['fps'], 
                             (props['width'], props['height']))
        
        # Process frames with progress bar
        progress_bar = tqdm(total=props['frame_count'], desc="Processing frames")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Apply processing function
            processed_frame = process_function(frame, **kwargs)
            
            # Write processed frame
            out.write(processed_frame)
            
            # Update progress
            progress_bar.update(1)
            
        # Close progress bar
        progress_bar.close()
        
        print(f"Processed video saved to {output_path}")
        
    finally:
        # Release resources
        cap.release()
        if 'out' in locals():
            out.release()


def release_resources(video_capture, video_writer=None):
    """
    Release video resources.
    
    Args:
        video_capture (cv2.VideoCapture): OpenCV VideoCapture object
        video_writer (cv2.VideoWriter, optional): OpenCV VideoWriter object
    """
    if video_capture is not None:
        video_capture.release()
        
    if video_writer is not None:
        video_writer.release()
