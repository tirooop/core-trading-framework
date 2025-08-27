"""
Generate dependency graph for WarMachine system using pyvis
"""

import os
import networkx as nx
from pyvis.network import Network
from typing import Dict, List, Set

def find_python_files(root_dir: str) -> List[str]:
    """Find all Python files in the directory"""
    python_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def parse_imports(file_path: str) -> List[str]:
    """Parse imports from a Python file"""
    imports = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            for line in lines:
                if line.startswith('import ') or line.startswith('from '):
                    # Extract module name
                    if line.startswith('from '):
                        module = line.split(' import ')[0].split('from ')[1]
                    else:
                        module = line.split(' import ')[1]
                    imports.append(module.split('.')[0])
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
    return imports

def build_dependency_graph(root_dir: str) -> nx.DiGraph:
    """Build dependency graph from Python files"""
    G = nx.DiGraph()
    
    # Find all Python files
    python_files = find_python_files(root_dir)
    
    # Add nodes and edges
    for file_path in python_files:
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        G.add_node(module_name, path=file_path)
        
        # Parse imports
        imports = parse_imports(file_path)
        for imp in imports:
            if imp in G:
                G.add_edge(module_name, imp)
    
    return G

def generate_visualization(G: nx.DiGraph, output_file: str):
    """Generate interactive visualization using pyvis"""
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black")
    
    # Add nodes
    for node in G.nodes():
        net.add_node(node, title=G.nodes[node].get('path', ''))
    
    # Add edges
    for edge in G.edges():
        net.add_edge(edge[0], edge[1])
    
    # Set physics layout
    net.set_options("""
    {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {
                "enabled": true,
                "iterations": 1000
            }
        }
    }
    """)
    
    # Save visualization
    net.save_graph(output_file)

def main():
    """Main function"""
    # Set paths
    root_dir = "warmachine"
    output_file = "dependency_graph.html"
    
    # Build graph
    print("Building dependency graph...")
    G = build_dependency_graph(root_dir)
    
    # Generate visualization
    print("Generating visualization...")
    generate_visualization(G, output_file)
    
    print(f"Visualization saved to {output_file}")

if __name__ == "__main__":
    main() 