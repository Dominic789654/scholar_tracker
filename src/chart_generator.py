import json
import plotly.graph_objects as go
import plotly.subplots as sp
import pandas as pd
from datetime import datetime

class ChartGenerator:
    def __init__(self, data_file, output_dir):
        self.data_file = data_file
        self.output_dir = output_dir
        
    def load_data(self):
        """Load citation history data"""
        with open(self.data_file, 'r') as f:
            history = json.load(f)
        return history
        
    def generate_charts(self):
        """Generate all charts"""
        history = self.load_data()
        
        # Convert to pandas DataFrame for easier handling
        df = pd.DataFrame([
            {
                'date': datetime.strptime(entry['date'], '%Y-%m-%d'),
                'total_citations': entry['total_citations'],
                'h_index': entry['h_index']
            } for entry in history
        ])
        
        # Sort by date
        df = df.sort_values('date')
        
        # Create figure with secondary y-axis
        fig = sp.make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add total citations line
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['total_citations'],
                name="Total Citations",
                line=dict(color='blue', width=2)
            ),
            secondary_y=False
        )
        
        # Add h-index line
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['h_index'],
                name="H-index",
                line=dict(color='red', width=2)
            ),
            secondary_y=True
        )
        
        # Update layout
        fig.update_layout(
            title="Citation Metrics Over Time",
            xaxis_title="Date",
            yaxis_title="Total Citations",
            yaxis2_title="H-index",
            hovermode='x unified',
            template='plotly_white'
        )
        
        # Save as HTML (interactive)
        fig.write_html(f"{self.output_dir}/citation_trends.html")
        
        # Save as PNG (static)
        fig.write_image(f"{self.output_dir}/citation_trends.png")
        
        # Generate individual paper trends
        self.generate_paper_trends(history)
        
    def generate_paper_trends(self, history):
        """Generate trends for individual papers"""
        # Create DataFrame for paper citations
        paper_data = []
        for entry in history:
            date = datetime.strptime(entry['date'], '%Y-%m-%d')
            for paper in entry['papers']:
                paper_data.append({
                    'date': date,
                    'title': paper['title'],
                    'citations': paper['citations']
                })
        
        df = pd.DataFrame(paper_data)
        
        # Create figure
        fig = go.Figure()
        
        # Add line for each paper
        for title in df['title'].unique():
            paper_df = df[df['title'] == title]
            fig.add_trace(
                go.Scatter(
                    x=paper_df['date'],
                    y=paper_df['citations'],
                    name=title,
                    mode='lines+markers'
                )
            )
        
        # Update layout
        fig.update_layout(
            title="Individual Paper Citations Over Time",
            xaxis_title="Date",
            yaxis_title="Citations",
            hovermode='x unified',
            template='plotly_white',
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=-0.2,
                xanchor="left",
                x=0
            )
        )
        
        # Save charts
        fig.write_html(f"{self.output_dir}/paper_trends.html")
        fig.write_image(f"{self.output_dir}/paper_trends.png") 