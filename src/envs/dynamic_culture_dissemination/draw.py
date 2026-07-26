import json
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from collections import Counter, defaultdict, deque
import pandas as pd
from pathlib import Path
import matplotlib as mpl
import matplotlib.patches as mpatches
import networkx as nx
from matplotlib.gridspec import GridSpec

# Set style for academic visualization
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.2)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['savefig.dpi'] = 300

# Generated metrics are resolved relative to this scenario directory.
base_path = Path(__file__).resolve().parent / "metrics_plots"

def find_latest_files(base_path):
    """Find the latest timestamp files across all rounds"""
    result = {}
    for round_num in range(0, 101):
        round_path = os.path.join(base_path, f"round_{round_num}", "profiles")
        if os.path.exists(round_path):
            files = [f for f in os.listdir(round_path) if f.startswith("profiles_")]
            if files:
                # Sort by timestamp to find the latest
                files.sort(reverse=True)
                result[round_num] = os.path.join(round_path, files[0])
    
    return result

def load_round_data(file_paths):
    """Load data from all rounds"""
    all_rounds_data = {}
    for round_num, file_path in file_paths.items():
        try:
            with open(file_path, 'r') as f:
                all_rounds_data[round_num] = json.load(f)
        except Exception as e:
            print(f"Error loading round {round_num}: {e}")
    
    return all_rounds_data

def create_enhanced_cultural_map(all_rounds_data, selected_rounds=[0, 25, 50, 100], output_dir="figures"):
    """
    Create an enhanced cultural similarity map showing boundaries between cultures
    with improved aesthetics compared to the original Axelrod visualization
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Create figure
    fig, axes = plt.subplots(1, len(selected_rounds), figsize=(16, 5))
    if len(selected_rounds) == 1:
        axes = [axes]
    
    # Define a custom gradient colormap for similarity boundaries
    # Creating a custom colormap from dark blue (low similarity) to white (high similarity)
    colors = [(0.0, 'midnightblue'), 
              (0.2, 'steelblue'),
              (0.4, 'skyblue'),
              (0.7, 'lightcyan'),
              (1.0, 'white')]
    
    similarity_cmap = LinearSegmentedColormap.from_list('similarity_cmap', colors)
    
    # Cultural traits for similarity calculation - excluding personality_trait
    traits = ['music_preference', 'culinary_preference', 'fashion_style', 
              'political_orientation', 'leisure_activity']
    
    for ax_idx, round_num in enumerate(selected_rounds):
        if round_num in all_rounds_data:
            round_data = all_rounds_data[round_num]
            
            # Create 10x10 grid of cultural data
            grid_data = []
            for i in range(100):
                if i < len(round_data):
                    agent = round_data[i]
                    culture = tuple(agent.get(trait, "") for trait in traits)
                    grid_data.append(culture)
                else:
                    grid_data.append(tuple([""] * len(traits)))
            
            # Calculate similarity between adjacent cells
            sim_grid_h = np.zeros((10, 9))  # Horizontal similarities
            sim_grid_v = np.zeros((9, 10))  # Vertical similarities
            
            # Calculate horizontal similarities
            for row in range(10):
                for col in range(9):
                    idx1 = row * 10 + col
                    idx2 = row * 10 + col + 1
                    culture1 = grid_data[idx1]
                    culture2 = grid_data[idx2]
                    
                    # Count matching traits
                    matches = sum(1 for a, b in zip(culture1, culture2) if a == b and a != "")
                    total = len(traits)
                    sim_grid_h[row, col] = matches / total if total > 0 else 0
            
            # Calculate vertical similarities
            for row in range(9):
                for col in range(10):
                    idx1 = row * 10 + col
                    idx2 = (row + 1) * 10 + col
                    culture1 = grid_data[idx1]
                    culture2 = grid_data[idx2]
                    
                    # Count matching traits
                    matches = sum(1 for a, b in zip(culture1, culture2) if a == b and a != "")
                    total = len(traits)
                    sim_grid_v[row, col] = matches / total if total > 0 else 0
            
            # Create plot with enhanced aesthetics
            ax = axes[ax_idx]
            
            # Draw grid cells with subtle background gradient
            for row in range(10):
                for col in range(10):
                    ax.add_patch(plt.Rectangle((col, row), 1, 1, fill=True, 
                                               color='whitesmoke', edgecolor='none'))
            
            # Enhanced visualization of cultural boundaries
            # Horizontal boundaries - line width increases as similarity decreases
            for row in range(10):
                for col in range(9):
                    sim = sim_grid_h[row, col]
                    line_width = 3.5 * (1 - sim) + 0.5  # Thicker lines for lower similarity
                    color = similarity_cmap(sim)
                    ax.plot([col+1, col+1], [row, row+1], color=color, linewidth=line_width, 
                           solid_capstyle='round')
            
            # Vertical boundaries - line width increases as similarity decreases
            for row in range(9):
                for col in range(10):
                    sim = sim_grid_v[row, col]
                    line_width = 3.5 * (1 - sim) + 0.5  # Thicker lines for lower similarity
                    color = similarity_cmap(sim)
                    ax.plot([col, col+1], [row+1, row+1], color=color, linewidth=line_width,
                           solid_capstyle='round')
            
            # Add subtle grid outline
            ax.add_patch(plt.Rectangle((0, 0), 10, 10, fill=False, 
                                      edgecolor='gray', linewidth=1.5, alpha=0.8))
            
            # Set plot properties
            ax.set_aspect('equal')
            ax.set_xlim(-0.2, 10.2)
            ax.set_ylim(10.2, -0.2)  # Reverse y-axis but add margin
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f'Round {round_num}', fontsize=14)
        
        else:
            axes[ax_idx].text(0.5, 0.5, f'Round {round_num} not available', 
                             ha='center', va='center')
            axes[ax_idx].axis('off')
    
    # Add custom legend
    # Create gradient color bar for similarity
    cax = fig.add_axes([0.25, 0.08, 0.5, 0.03])
    cb = mpl.colorbar.ColorbarBase(cax, cmap=similarity_cmap,
                                  orientation='horizontal')
    cb.set_label('Cultural Similarity Between Adjacent Cells')
    cb.set_ticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    cb.set_ticklabels(['0%', '20%', '40%', '60%', '80%', '100%'])
    
    plt.suptitle('Cultural Similarity Map', fontsize=16)
    plt.tight_layout(rect=[0, 0.15, 1, 0.95])
    
    # Save figure
    plt.savefig(os.path.join(output_dir, "enhanced_cultural_boundaries_map.png"), dpi=300, bbox_inches='tight')
    
    # Display in Jupyter
    plt.show()

def calculate_regions_and_zones(all_rounds_data, output_dir="figures"):
    """
    Calculate and visualize the evolution of cultural regions and zones over time
    - Region: Connected area with identical cultures
    - Zone: Connected area with at least one shared cultural trait
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate cultural regions and zones for each round
    regions_count = []
    zones_count = []
    rounds = sorted(all_rounds_data.keys())
    
    # Define traits excluding personality_trait
    traits = ['music_preference', 'culinary_preference', 'fashion_style', 
              'political_orientation', 'leisure_activity']
    
    for round_num in rounds:
        round_data = all_rounds_data[round_num]
        
        # Create 10x10 grid of cultural data
        grid = {}
        for i, agent in enumerate(round_data):
            if i < 100:  # Ensure we don't exceed grid size
                row, col = i // 10, i % 10
                culture = tuple(agent.get(trait, "") for trait in traits)
                grid[(row, col)] = culture
        
        # Calculate cultural regions (connected areas with identical cultures)
        regions = []
        visited = set()
        
        for i in range(10):
            for j in range(10):
                if (i, j) not in visited and (i, j) in grid:
                    # Start BFS
                    region = []
                    queue = [(i, j)]
                    culture = grid[(i, j)]
                    
                    while queue:
                        r, c = queue.pop(0)
                        if (r, c) in visited:
                            continue
                            
                        visited.add((r, c))
                        if (r, c) in grid and grid[(r, c)] == culture:
                            region.append((r, c))
                            
                            # Check all four directions
                            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                                nr, nc = r + dr, c + dc
                                if 0 <= nr < 10 and 0 <= nc < 10 and (nr, nc) not in visited:
                                    queue.append((nr, nc))
                    
                    if region:
                        regions.append(region)
        
        # Calculate cultural zones (connected areas with at least one shared trait)
        zones = []
        visited = set()
        
        for i in range(10):
            for j in range(10):
                if (i, j) not in visited and (i, j) in grid:
                    # Start BFS
                    zone = []
                    queue = [(i, j)]
                    
                    while queue:
                        r, c = queue.pop(0)
                        if (r, c) in visited:
                            continue
                            
                        visited.add((r, c))
                        current = (r, c)
                        zone.append(current)
                        
                        # Check all four directions
                        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                            nr, nc = r + dr, c + dc
                            neighbor = (nr, nc)
                            
                            if 0 <= nr < 10 and 0 <= nc < 10 and neighbor not in visited and neighbor in grid:
                                # Consider in same zone if at least one trait matches
                                curr_culture = grid[current]
                                neigh_culture = grid[neighbor]
                                
                                # Check if they share at least one trait
                                if any(c1 == c2 for c1, c2 in zip(curr_culture, neigh_culture)):
                                    queue.append(neighbor)
                    
                    if zone:
                        zones.append(zone)
        
        regions_count.append(len(regions))
        zones_count.append(len(zones))
    
    # Plot regions and zones over time with improved aesthetics
    plt.figure(figsize=(12, 8))
    
    # Create plot with gradient fill
    plt.semilogy(rounds, regions_count, '-', linewidth=2.5, color='#1f77b4', 
                label="Cultural Regions (Identical)")
    plt.semilogy(rounds, zones_count, '--', linewidth=2.5, color='#d62728', 
                label="Cultural Zones (At least one shared trait)")
    
    # Add light gradient fill under the curves
    plt.fill_between(rounds, regions_count, alpha=0.2, color='#1f77b4')
    plt.fill_between(rounds, zones_count, alpha=0.15, color='#d62728')
    
    plt.title('Cultural Regions and Zones Over Time', fontsize=16)
    plt.xlabel('Round', fontsize=14)
    plt.ylabel('Count (log scale)', fontsize=14)
    plt.legend(fontsize=12, loc='upper right')
    plt.grid(True, alpha=0.3)
    
    # Enhance x-axis
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    
    plt.tight_layout()
    
    # Save figure
    plt.savefig(os.path.join(output_dir, "cultural_regions_zones.png"), dpi=300)
    
    # Display in Jupyter
    plt.show()
    
    return regions_count, zones_count

def visualize_local_convergence_global_polarization(all_rounds_data, output_dir="figures"):
    """
    Create a visualization showing local convergence and global polarization:
    - Shows how cultural regions form locally while global diversity persists
    - Analyzes the size distribution of cultural regions over time
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Select key rounds for analysis
    rounds = sorted(all_rounds_data.keys())
    if len(rounds) >= 4:
        selected_rounds = [rounds[0], rounds[len(rounds)//3], rounds[2*len(rounds)//3], rounds[-1]]
    else:
        selected_rounds = rounds
    
    # Define traits excluding personality_trait
    traits = ['music_preference', 'culinary_preference', 'fashion_style', 
              'political_orientation', 'leisure_activity']
    
    # Create figure with 2 rows:
    # - Row 1: Cultural region maps showing how regions form
    # - Row 2: Region size distribution
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, len(selected_rounds), figure=fig, height_ratios=[1.5, 1])
    
    # Store region size data for each selected round
    region_sizes_data = []
    
    # For each selected round, visualize regions and calculate statistics
    for i, round_num in enumerate(selected_rounds):
        if round_num in all_rounds_data:
            round_data = all_rounds_data[round_num]
            
            # Create cultural region map
            grid = {}
            for idx, agent in enumerate(round_data):
                if idx < 100:
                    row, col = idx // 10, idx % 10
                    culture = tuple(agent.get(trait, "") for trait in traits)
                    grid[(row, col)] = culture
            
            # Find cultural regions
            regions = []
            visited = set()
            
            for r in range(10):
                for c in range(10):
                    if (r, c) not in visited and (r, c) in grid:
                        region = []
                        queue = [(r, c)]
                        culture = grid[(r, c)]
                        
                        while queue:
                            current_r, current_c = queue.pop(0)
                            if (current_r, current_c) in visited:
                                continue
                                
                            visited.add((current_r, current_c))
                            if (current_r, current_c) in grid and grid[(current_r, current_c)] == culture:
                                region.append((current_r, current_c))
                                
                                # Check neighbors
                                for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                                    nr, nc = current_r + dr, current_c + dc
                                    if 0 <= nr < 10 and 0 <= nc < 10 and (nr, nc) not in visited:
                                        queue.append((nr, nc))
                        
                        if region:
                            regions.append(region)
            
            # Create grid matrix of unique culture IDs
            region_grid = np.zeros((10, 10), dtype=int)
            culture_to_id = {}
            
            for r in range(10):
                for c in range(10):
                    if (r, c) in grid:
                        culture = grid[(r, c)]
                        if culture not in culture_to_id:
                            culture_to_id[culture] = len(culture_to_id) + 1
                        region_grid[r, c] = culture_to_id[culture]
            
            # Row 1: Visualize cultural regions
            ax1 = fig.add_subplot(gs[0, i])
            
            # Create a distinct colormap for cultural regions
            n_cultures = len(culture_to_id)
            if n_cultures <= 10:
                cmap = plt.cm.get_cmap('tab10', n_cultures)
            elif n_cultures <= 20:
                cmap = plt.cm.get_cmap('tab20', n_cultures)
            else:
                cmap = plt.cm.get_cmap('viridis', n_cultures)
            
            # Plot cultural regions with enhanced aesthetics
            im = ax1.imshow(region_grid, cmap=cmap, interpolation='nearest')
            
            # Draw grid lines
            for x in range(11):
                ax1.axhline(y=x-0.5, color='white', linestyle='-', linewidth=0.8, alpha=0.5)
                ax1.axvline(x=x-0.5, color='white', linestyle='-', linewidth=0.8, alpha=0.5)
            
            ax1.set_title(f'Round {round_num}', fontsize=14)
            ax1.set_xticks([])
            ax1.set_yticks([])
            
            # Store region sizes for analysis
            region_sizes = [len(region) for region in regions]
            region_sizes_data.append((round_num, region_sizes))
            
            # Row 2: Region size distribution
            ax2 = fig.add_subplot(gs[1, i])
            
            # Create distribution plot
            if region_sizes:
                # Create histogram of region sizes
                bins = np.arange(0.5, max(region_sizes) + 1.5, 1)
                ax2.hist(region_sizes, bins=bins, alpha=0.7, color='royalblue',
                        edgecolor='black', linewidth=1)
                
                # Add mean line
                mean_size = np.mean(region_sizes)
                ax2.axvline(mean_size, color='red', linestyle='--', linewidth=2, 
                           label=f'Mean: {mean_size:.1f}')
                
                # Calculate local convergence metrics
                largest_region = max(region_sizes)
                num_regions = len(regions)
                
                ax2.set_title(f'Regions: {num_regions}, Max Size: {largest_region}', fontsize=12)
                ax2.set_xlabel('Region Size', fontsize=12)
                ax2.set_ylabel('Frequency', fontsize=12)
                ax2.legend(fontsize=10)
                ax2.grid(True, alpha=0.3)
            else:
                ax2.text(0.5, 0.5, 'No regions found', ha='center', va='center')
                ax2.set_xticks([])
                ax2.set_yticks([])
    
    plt.suptitle('Local Convergence and Global Polarization', fontsize=18)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save figure
    plt.savefig(os.path.join(output_dir, "local_convergence_global_polarization.png"), dpi=300, bbox_inches='tight')
    
    # Display in Jupyter
    plt.show()
    
    # Create a summary table of convergence metrics
    plt.figure(figsize=(12, 6))
    
    # Prepare data for the summary table
    table_data = []
    table_columns = ['Round', 'Number of Regions', 'Average Region Size', 
                    'Largest Region Size', 'Local Convergence Index', 'Global Polarization Index']
    
    for round_num, sizes in region_sizes_data:
        if sizes:
            avg_size = np.mean(sizes)
            max_size = max(sizes)
            num_regions = len(sizes)
            
            # Calculate custom metrics
            local_convergence = avg_size / 100  # Normalized by grid size
            global_polarization = num_regions / 100  # Normalized by grid size
            
            table_data.append([
                round_num, 
                num_regions, 
                f"{avg_size:.2f}", 
                max_size,
                f"{local_convergence:.3f}",
                f"{global_polarization:.3f}"
            ])
    
    # Create the table
    ax = plt.gca()
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=table_data, colLabels=table_columns, loc='center',
                   cellLoc='center', colColours=['#f2f2f2']*len(table_columns))
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 1.5)
    
    plt.title('Cultural Convergence and Polarization Metrics', fontsize=16)
    plt.tight_layout()
    
    # Save figure
    plt.savefig(os.path.join(output_dir, "convergence_polarization_metrics.png"), dpi=300)
    
    # Display in Jupyter
    plt.show()

# Main execution function
def main():
    try:
        # Find latest files
        round_files = find_latest_files(base_path)
        print(f"Found {len(round_files)} round files")
        
        if not round_files:
            print("No files found. Check the base path.")
            return
        
        # Load data from all rounds
        all_rounds_data = load_round_data(round_files)
        print(f"Loaded data from {len(all_rounds_data)} rounds")
        
        # Create output directory
        output_dir = "axelrod_visualization_figures_100"
        os.makedirs(output_dir, exist_ok=True)
        
        # Create enhanced cultural similarity map
        create_enhanced_cultural_map(all_rounds_data, selected_rounds=[0, 10, 50,100], output_dir=output_dir)
        
        # Calculate and plot cultural regions and zones over time
        regions_count, zones_count = calculate_regions_and_zones(all_rounds_data, output_dir=output_dir)
        
        # Create visualization of local convergence and global polarization
        visualize_local_convergence_global_polarization(all_rounds_data, output_dir=output_dir)
        
        print(f"All visualizations have been saved to '{output_dir}' directory")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
