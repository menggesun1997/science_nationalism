#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World Map: Western vs Eastern Camps
Identify NATO countries and Shanghai Cooperation Organization countries with two colors
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE  # noqa: E402

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Try to import cartopy for real world maps
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    CARTOPY_AVAILABLE = True
    print("Using Cartopy for real world maps")
except ImportError:
    CARTOPY_AVAILABLE = False
    print("Cartopy not available, using matplotlib world map")
    try:
        import matplotlib.patches as mpatches
    except ImportError:
        pass

# Set English font
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 定义阵营国家列表
WEST_COUNTRIES = {
    # NATO成员国
    'ALBANIA', 'BELGIUM', 'BULGARIA', 'CANADA', 'CROATIA', 'CZECH REPUBLIC', 
    'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 'GERMANY', 'GREECE', 'HUNGARY', 
    'ICELAND', 'ITALY', 'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MONTENEGRO', 
    'NETHERLANDS', 'NORTH MACEDONIA', 'NORWAY', 'POLAND', 'PORTUGAL', 'ROMANIA', 
    'SLOVAKIA', 'SLOVENIA', 'SPAIN', 'TURKEY', 'UNITED KINGDOM', 'UNITED STATES'
}

EAST_COUNTRIES = {
    # 上海合作组织成员国
    'CHINA', 'RUSSIAN FEDERATION', 'KAZAKHSTAN', 'KYRGYZSTAN', 'TAJIKISTAN', 
    'UZBEKISTAN', 'INDIA', 'PAKISTAN'
}

# 国家名称映射（处理一些特殊名称）
COUNTRY_MAPPING = {
    'CZECH REPUBLIC': 'CZECHIA',
    'RUSSIAN FEDERATION': 'RUSSIA',
    'UNITED KINGDOM': 'UK',
    'UNITED STATES': 'USA'
}

def create_world_map():
    """Create world map identifying Western and Eastern camps"""
    
    if CARTOPY_AVAILABLE:
        # Use Cartopy for real world maps
        fig = plt.figure(figsize=(20, 12))
        ax = plt.axes(projection=ccrs.Robinson())
        
        # Add natural earth features
        ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
        ax.add_feature(cfeature.OCEAN, facecolor='lightblue', alpha=0.3)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.3)
        ax.add_feature(cfeature.LAKES, facecolor='lightblue', alpha=0.3)
        
        # Set global extent
        ax.set_global()
        
    else:
        # Fallback to matplotlib with better continent shapes
        fig, ax = plt.subplots(1, 1, figsize=(20, 12))
        
        # Set map background
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        ax.set_aspect('equal')
        
        # Draw world map outline using more realistic continent shapes
        # North America
        north_america_x = [-140, -140, -130, -120, -110, -100, -90, -80, -70, -60, -50, -50, -60, -70, -80, -90, -100, -110, -120, -130, -140]
        north_america_y = [15, 25, 35, 45, 55, 65, 70, 75, 75, 70, 65, 55, 45, 35, 25, 20, 15, 15, 15, 15, 15]
        ax.fill(north_america_x, north_america_y, color='lightgray', alpha=0.3, edgecolor='black', linewidth=1)
        
        # South America
        south_america_x = [-80, -80, -75, -70, -65, -60, -55, -50, -45, -40, -35, -35, -40, -45, -50, -55, -60, -65, -70, -75, -80]
        south_america_y = [15, 5, -5, -15, -25, -35, -45, -50, -55, -55, -50, -40, -30, -20, -10, 0, 5, 10, 12, 15, 15]
        ax.fill(south_america_x, south_america_y, color='lightgray', alpha=0.3, edgecolor='black', linewidth=1)
        
        # Europe
        europe_x = [-10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 40, 35, 30, 25, 20, 15, 10, 5, 0, -5, -10]
        europe_y = [35, 40, 45, 50, 55, 60, 65, 70, 75, 75, 70, 60, 55, 50, 45, 40, 35, 35, 35, 35, 35, 35]
        ax.fill(europe_x, europe_y, color='lightgray', alpha=0.3, edgecolor='black', linewidth=1)
        
        # Africa
        africa_x = [-20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 50, 45, 40, 35, 30, 25, 20, 15, 10, 5, 0, -5, -10, -15, -20]
        africa_y = [-35, -30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 25, 20, 15, 10, 5, 0, -5, -10, -15, -20, -25, -30, -35, -35, -35]
        ax.fill(africa_x, africa_y, color='lightgray', alpha=0.3, edgecolor='black', linewidth=1)
        
        # Asia
        asia_x = [40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 180, 170, 160, 150, 140, 130, 120, 110, 100, 90, 80, 70, 60, 50, 40]
        asia_y = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 75, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 15, 15, 12, 10]
        ax.fill(asia_x, asia_y, color='lightgray', alpha=0.3, edgecolor='black', linewidth=1)
        
        # Australia
        australia_x = [110, 120, 130, 140, 150, 155, 155, 150, 140, 130, 120, 110, 110]
        australia_y = [-45, -40, -35, -30, -25, -20, -15, -10, -10, -15, -20, -25, -45]
        ax.fill(australia_x, australia_y, color='lightgray', alpha=0.3, edgecolor='black', linewidth=1)
    
    # 定义国家位置（经度，纬度）
    country_positions = {
        # 西方阵营（NATO）- 蓝色
        'ALBANIA': (20, 41), 'BELGIUM': (4, 51), 'BULGARIA': (25, 43), 
        'CANADA': (-95, 60), 'CROATIA': (16, 45), 'CZECH REPUBLIC': (15, 50), 
        'DENMARK': (10, 56), 'ESTONIA': (26, 59), 'FINLAND': (26, 64), 
        'FRANCE': (2, 47), 'GERMANY': (10, 51), 'GREECE': (22, 39), 
        'HUNGARY': (20, 47), 'ICELAND': (-18, 65), 'ITALY': (12, 42), 
        'LATVIA': (25, 57), 'LITHUANIA': (24, 56), 'LUXEMBOURG': (6, 50), 
        'MONTENEGRO': (19, 42), 'NETHERLANDS': (5, 52), 'NORTH MACEDONIA': (22, 42), 
        'NORWAY': (10, 62), 'POLAND': (20, 52), 'PORTUGAL': (-8, 39), 
        'ROMANIA': (25, 46), 'SLOVAKIA': (19, 49), 'SLOVENIA': (15, 46), 
        'SPAIN': (-3, 40), 'TURKEY': (35, 39), 'UNITED KINGDOM': (-2, 54), 
        'UNITED STATES': (-100, 40),
        
        # 东方阵营（上海合作组织）- 红色
        'CHINA': (105, 35), 'RUSSIAN FEDERATION': (100, 60), 'KAZAKHSTAN': (68, 48), 
        'KYRGYZSTAN': (75, 41), 'TAJIKISTAN': (71, 39), 'UZBEKISTAN': (64, 41), 
        'INDIA': (78, 20), 'PAKISTAN': (70, 30)
    }
    
    # Plot country markers
    west_x, west_y = [], []
    east_x, east_y = [], []
    west_names, east_names = [], []
    
    for country, pos in country_positions.items():
        # Check which camp the country belongs to
        if country in WEST_COUNTRIES:
            west_x.append(pos[0])
            west_y.append(pos[1])
            west_names.append(country)
        elif country in EAST_COUNTRIES:
            east_x.append(pos[0])
            east_y.append(pos[1])
            east_names.append(country)
    
    # Plot Western camp countries (blue)
    if CARTOPY_AVAILABLE:
        # For Cartopy, we need to transform coordinates
        ax.scatter(west_x, west_y, c='blue', s=100, alpha=0.8, label='Western Camp (NATO)', 
                  zorder=5, transform=ccrs.PlateCarree())
        ax.scatter(east_x, east_y, c='red', s=100, alpha=0.8, label='Eastern Camp (SCO)', 
                  zorder=5, transform=ccrs.PlateCarree())
    else:
        # For matplotlib
        ax.scatter(west_x, west_y, c='blue', s=100, alpha=0.8, label='Western Camp (NATO)', zorder=5)
        ax.scatter(east_x, east_y, c='red', s=100, alpha=0.8, label='Eastern Camp (SCO)', zorder=5)
    
    # Add country labels
    for country, pos in country_positions.items():
        # Simplify country name display
        display_name = country.replace('REPUBLIC', '').replace('FEDERATION', '').replace('UNITED ', '').replace('KINGDOM', 'UK')
        if len(display_name) > 8:
            display_name = display_name[:8] + '...'
        
        if CARTOPY_AVAILABLE:
            ax.annotate(display_name, (pos[0], pos[1]), 
                       xytext=(5, 5), textcoords='offset points', 
                       fontsize=8, ha='left', va='bottom',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7),
                       transform=ccrs.PlateCarree())
        else:
            ax.annotate(display_name, (pos[0], pos[1]), 
                       xytext=(5, 5), textcoords='offset points', 
                       fontsize=8, ha='left', va='bottom',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
    
    # Add legend
    ax.legend(loc='upper right', fontsize=12, framealpha=0.9)
    
    # Set title and labels
    if CARTOPY_AVAILABLE:
        ax.set_title('World Map: Western vs Eastern Camps\nNATO Countries vs Shanghai Cooperation Organization', 
                    fontsize=16, fontweight='bold', pad=20)
    else:
        ax.set_title('World Map: Western vs Eastern Camps\nNATO Countries vs Shanghai Cooperation Organization', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Set axis ticks
        ax.set_xticks(range(-180, 181, 30))
        ax.set_yticks(range(-90, 91, 30))
    
    # Add camp information
    west_countries_sample = ', '.join(sorted(list(WEST_COUNTRIES))[:10])
    east_countries_list = ', '.join(sorted(list(EAST_COUNTRIES)))
    info_text = f"""Camp Information:
• Blue: Western Camp (NATO) - {len(WEST_COUNTRIES)} countries
• Red: Eastern Camp (SCO) - {len(EAST_COUNTRIES)} countries

NATO Members: {west_countries_sample}...
SCO Members: {east_countries_list}"""
    
    ax.text(0.02, 0.02, info_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='bottom', bbox=dict(boxstyle='round,pad=0.5', 
            facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    # Save chart
    output_dir = str(CODE / "1netoworks_did_russia_ukraine")
    import os
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, 'world_map_western_vs_eastern_camps.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"World map saved to: {filepath}")
    
    plt.show()
    
    return fig

def create_detailed_camp_analysis():
    """Create detailed camp analysis charts"""
    
    # Create subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
    
    # 1. Camp country count comparison
    camp_counts = [len(WEST_COUNTRIES), len(EAST_COUNTRIES)]
    camp_labels = ['Western Camp\n(NATO)', 'Eastern Camp\n(SCO)']
    colors = ['blue', 'red']
    
    bars1 = ax1.bar(camp_labels, camp_counts, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_title('Number of Countries by Camp', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Number of Countries')
    
    # Add value labels on bars
    for bar, count in zip(bars1, camp_counts):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{count}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # 2. Geographic distribution pie chart
    # Group by continent
    europe_countries = {'ALBANIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CZECH REPUBLIC', 
                       'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 'GERMANY', 'GREECE', 
                       'HUNGARY', 'ICELAND', 'ITALY', 'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 
                       'MONTENEGRO', 'NETHERLANDS', 'NORTH MACEDONIA', 'NORWAY', 'POLAND', 
                       'PORTUGAL', 'ROMANIA', 'SLOVAKIA', 'SLOVENIA', 'SPAIN', 'TURKEY', 
                       'UNITED KINGDOM'}
    
    asia_countries = {'CHINA', 'RUSSIAN FEDERATION', 'KAZAKHSTAN', 'KYRGYZSTAN', 
                      'TAJIKISTAN', 'UZBEKISTAN', 'INDIA', 'PAKISTAN'}
    
    americas_countries = {'CANADA', 'UNITED STATES'}
    
    region_counts = [len(europe_countries), len(asia_countries), len(americas_countries)]
    region_labels = ['Europe', 'Asia', 'Americas']
    region_colors = ['lightblue', 'lightcoral', 'lightgreen']
    
    ax2.pie(region_counts, labels=region_labels, colors=region_colors, autopct='%1.1f%%', 
            startangle=90)
    ax2.set_title('Geographic Distribution of Camp Countries', fontsize=14, fontweight='bold')
    
    # 3. Camp country lists
    west_list = '\n'.join([f"• {country}" for country in sorted(list(WEST_COUNTRIES))])
    east_list = '\n'.join([f"• {country}" for country in sorted(list(EAST_COUNTRIES))])
    
    ax3.text(0.1, 0.9, 'Western Camp (NATO):', transform=ax3.transAxes, 
             fontsize=12, fontweight='bold', verticalalignment='top')
    ax3.text(0.1, 0.8, west_list, transform=ax3.transAxes, 
             fontsize=10, verticalalignment='top')
    ax3.set_title('Western Camp Countries', fontsize=14, fontweight='bold')
    ax3.axis('off')
    
    ax4.text(0.1, 0.9, 'Eastern Camp (SCO):', transform=ax4.transAxes, 
             fontsize=12, fontweight='bold', verticalalignment='top')
    ax4.text(0.1, 0.8, east_list, transform=ax4.transAxes, 
             fontsize=10, verticalalignment='top')
    ax4.set_title('Eastern Camp Countries', fontsize=14, fontweight='bold')
    ax4.axis('off')
    
    plt.suptitle('Detailed Analysis: Western vs Eastern Camps', fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    # Save chart
    output_dir = str(CODE / "1netoworks_did_russia_ukraine")
    import os
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, 'detailed_camp_analysis.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"Detailed camp analysis chart saved to: {filepath}")
    
    plt.show()
    
    return fig

def main():
    """Main function"""
    print("=" * 80)
    print("World Map: Western vs Eastern Camps")
    print("=" * 80)
    print(f"Western Camp (NATO): {len(WEST_COUNTRIES)} countries")
    print(f"Eastern Camp (SCO): {len(EAST_COUNTRIES)} countries")
    print("=" * 80)
    
    # Create world map
    print("Creating world map...")
    world_map = create_world_map()
    
    # Create detailed analysis chart
    print("Creating detailed camp analysis chart...")
    detailed_analysis = create_detailed_camp_analysis()
    
    print("\n" + "=" * 80)
    print("Map creation completed!")
    print("=" * 80)
    print("Generated files:")
    print("1. world_map_western_vs_eastern_camps.png - World Map")
    print("2. detailed_camp_analysis.png - Detailed Camp Analysis")
    print("=" * 80)

if __name__ == "__main__":
    main()
