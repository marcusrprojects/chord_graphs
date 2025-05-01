# chord_generator.py

import itertools
import argparse
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_pdf import PdfPages
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Core Chord Logic ---

def generate_chord_structure(root, chord_type, inversion=0):
    """
    Generates the notes and structure for a given musical chord.

    Args:
        root (str): The root note of the chord (e.g., "C", "G#").
        chord_type (str): The type of chord (e.g., "major", "minor", "7", "minor7", "maj7").
        inversion (int): The inversion number (0 for root position, 1 for first inversion, etc.).

    Returns:
        tuple: A tuple containing:
            - list[str]: Names of the notes in the chord.
            - list[str]: Key types ("white" or "black") for each note.
            - str: A title string for the chord diagram.

    Raises:
        ValueError: If the chord_type is unsupported or the root note is invalid.
    """
    intervals = {
        "major": [0, 4, 7],
        "minor": [0, 3, 7],
        "7": [0, 4, 7, 10],
        "minor7": [0, 3, 7, 10],
        "maj7": [0, 4, 7, 11],
    }

    chromatic_scale = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    key_types = ["white", "black", "white", "black", "white", "white", "black", "white", "black", "white", "black", "white"]

    if chord_type not in intervals:
        raise ValueError(f"Unsupported chord type: {chord_type}")
    if root not in chromatic_scale:
         raise ValueError(f"Invalid root note: {root}")

    chord_intervals = intervals[chord_type][:] # Make a copy to avoid modifying original

    # Apply inversion
    num_notes = len(chord_intervals)
    actual_inversion = inversion % num_notes
    for _ in range(actual_inversion):
         # Pop lowest note and add 12 semitones (octave up)
        chord_intervals.append(chord_intervals.pop(0) + 12)
    chord_intervals.sort() # Keep intervals sorted for consistent note order

    root_index = chromatic_scale.index(root)
    chord_notes_indices = [(root_index + interval) % 12 for interval in chord_intervals]
    chord_note_names = [chromatic_scale[note_index] for note_index in chord_notes_indices]
    key_colors = [key_types[note_index] for note_index in chord_notes_indices]

    inversion_str = f"(Inversion {actual_inversion})" if actual_inversion > 0 else "(Root Position)"
    title = f"{root} {chord_type} {inversion_str}"

    return chord_note_names, key_colors, title

def plot_chord_diagram(chord_note_names, key_colors, title):
    """
    Plots the chord diagram using Matplotlib and NetworkX.

    Args:
        chord_note_names (list[str]): Names of the notes in the chord.
        key_colors (list[str]): Key types ("white" or "black") for each note.
        title (str): The title for the plot.
    """
    graph = nx.Graph()
    positions = {}
    node_colors_map = []

    for i, note in enumerate(chord_note_names):
        key_color_value = (.2, .2, .2) if key_colors[i] == "black" else "whitesmoke"
        text_color = "white" if key_colors[i] == "black" else "black"
        # Ensure unique node names if duplicates exist (e.g., in inversions)
        node_id = f"{note}_{i}"
        graph.add_node(node_id, label=note, color=key_color_value, text_color=text_color)
        node_colors_map.append(key_color_value)
        # Position black keys slightly higher
        positions[node_id] = (i, 0.1 if key_colors[i] == "black" else 0)

    # Connect the notes (visually, not necessarily musically adjacent)
    node_ids = list(graph.nodes())
    for i in range(len(node_ids) - 1):
        graph.add_edge(node_ids[i], node_ids[i+1])
    # Optional: Connect first and last node for a cycle
    # if len(node_ids) > 1:
    #    graph.add_edge(node_ids[-1], node_ids[0])

    plt.figure(figsize=(8, 4)) # Adjusted figure size
    nx.draw(
        graph,
        pos=positions,
        with_labels=False,
        node_size=2500,
        node_color=node_colors_map,
        edge_color="gray",
        width=1.5,
    )

    # Add labels with appropriate text colors
    for node_id, (x, y) in positions.items():
        node_attr = graph.nodes[node_id]
        plt.text(
            x, y, node_attr['label'],
            fontsize=14,
            fontweight='bold',
            ha="center",
            va="center",
            color=node_attr['text_color']
        )

    plt.title(title, color="gray", fontsize=20, pad=20)
    plt.axis("off")
    plt.tight_layout()

# --- Main Execution ---

def main():
    """
    Main function to parse arguments and generate chord diagrams.
    """
    parser = argparse.ArgumentParser(description="Generate musical chord diagrams and save them to PDF.")
    parser.add_argument("-r", "--roots", nargs='+', default=["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"],
                        help="List of root notes (e.g., C G# F). Defaults to all 12 chromatic notes.")
    parser.add_argument("-t", "--types", nargs='+', default=["major", "minor", "7", "minor7", "maj7"],
                        help="List of chord types (e.g., major 7 maj7). Defaults to major, minor, 7, minor7, maj7.")
    parser.add_argument("-i", "--inversions", type=int, nargs='+', default=[0, 1, 2, 3],
                        help="List of inversion numbers (e.g., 0 1 2). Defaults to 0, 1, 2, 3.")
    parser.add_argument("-o", "--output", default="chord_diagrams.pdf",
                        help="Output PDF filename. Defaults to 'chord_diagrams.pdf'.")
    parser.add_argument("--skip-root", action='store_true',
                        help="Skip generating root position chords (only generate inversions).")


    args = parser.parse_args()

    # Validate chord types and roots from arguments
    valid_types = {"major", "minor", "7", "minor7", "maj7"}
    valid_roots = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"}

    for chord_type in args.types:
        if chord_type not in valid_types:
            logging.error(f"Invalid chord type specified: {chord_type}. Valid types are: {', '.join(valid_types)}")
            return # Exit if invalid type
    for root in args.roots:
         if root not in valid_roots:
             logging.error(f"Invalid root note specified: {root}. Valid roots are: {', '.join(valid_roots)}")
             return # Exit if invalid root


    logging.info(f"Generating diagrams for roots: {', '.join(args.roots)}")
    logging.info(f"Chord types: {', '.join(args.types)}")
    logging.info(f"Inversions: {', '.join(map(str, args.inversions))}")
    logging.info(f"Output file: {args.output}")

    count = 0
    with PdfPages(args.output) as pdf:
        for root in args.roots:
            for chord_type in args.types:
                # Determine which inversions to generate for this chord type
                num_notes = len({
                    "major": [0, 4, 7], "minor": [0, 3, 7], "7": [0, 4, 7, 10],
                    "minor7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11]
                }[chord_type])
                
                active_inversions = [inv for inv in args.inversions if inv < num_notes]
                if args.skip_root and 0 in active_inversions:
                     active_inversions.remove(0)
                if not args.skip_root and 0 not in active_inversions : # Ensure root is added if not skipped and not present
                     active_inversions.insert(0,0)
                
                active_inversions = sorted(list(set(active_inversions))) # Unique & sorted


                for inversion in active_inversions:
                    try:
                        notes, keys, title = generate_chord_structure(root, chord_type, inversion)
                        plot_chord_diagram(notes, keys, title)
                        pdf.savefig(bbox_inches="tight") # Save the current figure to the PDF
                        plt.close() # Close the figure to free memory
                        count += 1
                        logging.info(f"Generated: {title}")
                    except ValueError as e:
                        logging.error(f"Could not generate '{root} {chord_type}' (Inversion {inversion}): {e}")
                    except Exception as e:
                        logging.error(f"An unexpected error occurred generating '{root} {chord_type}' (Inversion {inversion}): {e}")


    logging.info(f"Finished! Created {args.output} containing {count} chord diagrams.")

if __name__ == "__main__":
    main()