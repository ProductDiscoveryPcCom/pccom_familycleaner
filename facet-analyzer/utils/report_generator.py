"""
Generador de Reportes HTML
"""
import json
from typing import Dict, List, Any
from datetime import datetime
import pandas as pd


class ReportGenerator:
    """Genera reportes HTML dinámicos"""
    
    def __init__(self, category: str, data: Dict[str, Any]):
        self.category = category
        self.data = data
        
    def _format_number(self, num: float) -> str:
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return f"{num:,.0f}"
    
    def _get_css_base(self) -> str:
        return """
        :root {
            --bg-primary: #0a0a12;
            --bg-secondary: #12121f;
            --bg-card: #1a1a2e;
            --accent-cyan: #00d9ff;
            --accent-green: #00ff88;
            --accent-yellow: #ffd93d;
            --accent-red: #ff6b6b;
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --border-color: rgba(255,255,255,0.1);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .header {
            text-align: center;
            padding: 3rem 2rem;
            background: linear-gradient(135deg, rgba(0,217,255,0.15), rgba(168,85,247,0.1));
            border-radius: 24px;
            margin-bottom: 3rem;
        }
        .header h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            margin-bottom: 1.5rem;
        }
        .metrics-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin-bottom: 2rem; }
        .metric { text-align: center; padding: 1.5rem; background: var(--bg-card); border-radius: 12px; }
        .metric-value { font-size: 2rem; font-weight: 700; color: var(--accent-cyan); }
        .metric-label { font-size: 0.85rem; color: var(--text-secondary); }
        .footer { text-align: center; padding: 2rem; color: var(--text-secondary); margin-top: 3rem; }
        """
    
    def generate_architecture_report(self) -> str:
        metrics = self.data.get('metrics', {})
        architecture = self.data.get('architecture', {})
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Arquitectura | {self.category.title()}</title>
    <style>{self._get_css_base()}</style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🏗️ Arquitectura de Facetas</h1>
            <p style="color: #888; margin-top: 0.5rem;">{self.category.title()}</p>
        </header>
        <div class="metrics-row">
            <div class="metric">
                <div class="metric-value">{self._format_number(metrics.get('total_internal_sessions', 0))}</div>
                <div class="metric-label">Sesiones</div>
            </div>
            <div class="metric">
                <div class="metric-value">{self._format_number(architecture.get('total_urls', 0))}</div>
                <div class="metric-label">URLs</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.get('seo_ratio', 0):.0f}%</div>
                <div class="metric-label">Ratio SEO</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(self.data.get('insights', []))}</div>
                <div class="metric-label">Insights</div>
            </div>
        </div>
        <div class="card">
            <h3>Distribución por Nivel</h3>
            <p style="color: #888; margin-top: 1rem;">Datos generados el {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        <footer class="footer">
            <p>Arquitectura Report | {self.category.title()}</p>
        </footer>
    </div>
</body>
</html>"""
    
    def generate_market_share_report(self) -> str:
        brand_data = self.data.get('brand_analysis', [])
        
        brand_rows = ""
        for b in brand_data[:10]:
            brand_rows += f"<tr><td>{b.get('brand', '').title()}</td><td>{b.get('internal_share', 0):.1f}%</td><td>{b.get('seo_share', 0):.1f}%</td></tr>"
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Market Share | {self.category.title()}</title>
    <style>
        {self._get_css_base()}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 1rem; text-align: left; border-bottom: 1px solid var(--border-color); }}
        th {{ background: rgba(0,217,255,0.1); color: var(--accent-cyan); }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🏆 Market Share por Marca</h1>
            <p style="color: #888; margin-top: 0.5rem;">{self.category.title()}</p>
        </header>
        <div class="card">
            <h3>Ranking de Marcas</h3>
            <table>
                <thead><tr><th>Marca</th><th>Share UX</th><th>Share SEO</th></tr></thead>
                <tbody>{brand_rows}</tbody>
            </table>
        </div>
        <footer class="footer">
            <p>Market Share Report | {datetime.now().strftime('%Y-%m-%d')}</p>
        </footer>
    </div>
</body>
</html>"""
    
    def generate_content_strategy_report(self) -> str:
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Content Strategy | {self.category.title()}</title>
    <style>{self._get_css_base()}</style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📝 Content Strategy</h1>
            <p style="color: #888; margin-top: 0.5rem;">{self.category.title()}</p>
        </header>
        <div class="card">
            <h3>Estrategia de Contenido</h3>
            <p style="color: #888; margin-top: 1rem;">Análisis de contenido informacional vs transaccional.</p>
        </div>
        <footer class="footer">
            <p>Content Strategy Report | {datetime.now().strftime('%Y-%m-%d')}</p>
        </footer>
    </div>
</body>
</html>"""
    
    def generate_executive_summary(self) -> str:
        insights = self.data.get('insights', [])
        metrics = self.data.get('metrics', {})
        
        insights_html = ""
        for i, insight in enumerate(insights[:10]):
            color = '#ff6b6b' if insight.get('priority') == 'HIGH' else '#ffd93d' if insight.get('priority') == 'MEDIUM' else '#00ff88'
            insights_html += f"""
            <div style="padding: 1rem; background: var(--bg-secondary); border-radius: 12px; margin-bottom: 0.8rem; border-left: 4px solid {color};">
                <strong>{insight.get('title', '')}</strong>
                <p style="color: #888; font-size: 0.9rem; margin-top: 0.3rem;">{insight.get('description', '')}</p>
            </div>
            """
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Resumen Ejecutivo | {self.category.title()}</title>
    <style>{self._get_css_base()}</style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📋 Resumen Ejecutivo</h1>
            <p style="color: #888; margin-top: 0.5rem;">{self.category.title()}</p>
        </header>
        <div class="metrics-row">
            <div class="metric">
                <div class="metric-value">{self._format_number(metrics.get('total_internal_sessions', 0))}</div>
                <div class="metric-label">Sesiones</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.get('seo_ratio', 0):.0f}%</div>
                <div class="metric-label">Ratio SEO</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(insights)}</div>
                <div class="metric-label">Insights</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(self.data.get('brand_analysis', []))}</div>
                <div class="metric-label">Marcas</div>
            </div>
        </div>
        <div class="card">
            <h3>💡 Insights Clave</h3>
            <div style="margin-top: 1rem;">
                {insights_html if insights_html else '<p style="color: #888;">Sin insights disponibles</p>'}
            </div>
        </div>
        <footer class="footer">
            <p>Executive Summary | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </footer>
    </div>
</body>
</html>"""
