"""
Generador de Reportes HTML Dinámicos
Genera dashboards visuales basados en los datos analizados
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd


class ReportGenerator:
    """Genera reportes HTML dinámicos basados en datos de análisis"""
    
    def __init__(self, category: str, data: Dict[str, Any]):
        self.category = category
        self.data = data
        self.insights = []
        
    def _format_number(self, num: float) -> str:
        """Formatea números para visualización"""
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return f"{num:,.0f}"
    
    def _get_css_base(self) -> str:
        """CSS base compartido por todos los reportes"""
        return """
        :root {
            --bg-primary: #0a0a12;
            --bg-secondary: #12121f;
            --bg-card: #1a1a2e;
            --accent-cyan: #00d9ff;
            --accent-green: #00ff88;
            --accent-yellow: #ffd93d;
            --accent-red: #ff6b6b;
            --accent-purple: #a855f7;
            --accent-blue: #3b82f6;
            --accent-orange: #f97316;
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
        .container { max-width: 1500px; margin: 0 auto; padding: 2rem; }
        
        .header {
            text-align: center;
            padding: 3rem 2rem;
            background: linear-gradient(135deg, rgba(0,217,255,0.15), rgba(168,85,247,0.1));
            border-radius: 24px;
            margin-bottom: 3rem;
            border: 1px solid var(--border-color);
        }
        .header h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p { color: var(--text-secondary); margin-top: 0.5rem; }
        .header .category {
            display: inline-block;
            background: var(--accent-purple);
            color: white;
            padding: 0.5rem 1.5rem;
            border-radius: 30px;
            font-weight: 600;
            margin-top: 1rem;
        }
        
        .metrics-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }
        .metric-card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            text-align: center;
        }
        .metric-icon { font-size: 2rem; margin-bottom: 0.5rem; }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric-label { color: var(--text-secondary); font-size: 0.9rem; }
        
        .section { margin-bottom: 3rem; }
        .section-title {
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        .section-line {
            flex: 1;
            height: 2px;
            background: linear-gradient(90deg, var(--accent-cyan), transparent);
        }
        
        .cards-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; }
        .cards-grid-3 { grid-template-columns: repeat(3, 1fr); }
        .card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }
        .card-full { grid-column: 1 / -1; }
        .card h3 { margin-bottom: 1rem; }
        
        .chart-container { height: 350px; position: relative; }
        
        .data-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        .data-table th, .data-table td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        .data-table th {
            background: rgba(0,217,255,0.1);
            color: var(--accent-cyan);
            font-size: 0.8rem;
            text-transform: uppercase;
        }
        
        .insight-box {
            background: linear-gradient(135deg, rgba(0,217,255,0.1), rgba(0,255,136,0.05));
            border: 1px solid rgba(0,217,255,0.2);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
        }
        .insight-box h4 { color: var(--accent-cyan); margin-bottom: 0.5rem; }
        .insight-box ul { padding-left: 1.5rem; color: var(--text-secondary); }
        .insight-box li { margin-bottom: 0.5rem; }
        
        .recommendation {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.2rem;
            margin-bottom: 1rem;
            border-left: 4px solid var(--accent-cyan);
            display: flex;
            align-items: flex-start;
            gap: 1rem;
        }
        .recommendation.critical { border-left-color: var(--accent-red); }
        .recommendation.important { border-left-color: var(--accent-yellow); }
        .recommendation.success { border-left-color: var(--accent-green); }
        .rec-number {
            width: 32px; height: 32px;
            background: var(--accent-cyan);
            color: var(--bg-primary);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            flex-shrink: 0;
        }
        .recommendation.critical .rec-number { background: var(--accent-red); color: white; }
        .rec-content h4 { font-size: 0.95rem; margin-bottom: 0.3rem; }
        .rec-content p { font-size: 0.85rem; color: var(--text-secondary); }
        
        .progress-bar {
            height: 8px;
            background: var(--bg-secondary);
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-fill { height: 100%; border-radius: 4px; }
        
        .badge {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge.high { background: rgba(255,107,107,0.2); color: var(--accent-red); }
        .badge.medium { background: rgba(255,217,61,0.2); color: var(--accent-yellow); }
        .badge.low { background: rgba(0,255,136,0.2); color: var(--accent-green); }
        
        .footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            border-top: 1px solid var(--border-color);
            margin-top: 3rem;
        }
        
        @media (max-width: 768px) {
            .cards-grid, .cards-grid-3 { grid-template-columns: 1fr; }
            .metrics-row { grid-template-columns: repeat(2, 1fr); }
        }
        """
    
    def generate_architecture_report(self) -> str:
        """Genera el reporte de arquitectura de facetas con análisis de niveles"""
        
        # Extraer datos
        facet_usage = self.data.get('facet_usage', {})
        size_data = self.data.get('size_analysis', [])
        brand_data = self.data.get('brand_analysis', [])
        tech_data = self.data.get('tech_analysis', [])
        metrics = self.data.get('metrics', {})
        insights = self.data.get('insights', [])
        architecture = self.data.get('architecture', {})
        architecture_seo = self.data.get('architecture_seo', {})
        
        # Preparar datos para gráficos de niveles
        level_dist = architecture.get('level_distribution', [])
        level_labels = json.dumps([f'N{l["level"]}' for l in level_dist[:6]])
        level_ux_values = json.dumps([l.get('sessions', 0) for l in level_dist[:6]])
        
        # Datos SEO si existen
        level_seo_dist = architecture_seo.get('level_distribution', [])
        level_seo_values = json.dumps([l.get('sessions', 0) for l in level_seo_dist[:6]]) if level_seo_dist else '[]'
        
        # Preparar datos para gráficos de facetas
        facet_chart_data = json.dumps([
            {'label': k.replace('_', ' ').title(), 'value': v.get('pct_all', 0)}
            for k, v in sorted(facet_usage.items(), key=lambda x: -x[1].get('sessions_all', 0))[:6]
        ])
        
        # Generar tabla de distribución por nivel
        level_rows = ""
        for level in level_dist[:7]:
            seo_data = next((l for l in level_seo_dist if l['level'] == level['level']), {})
            seo_sessions = seo_data.get('sessions', 0)
            seo_pct = seo_data.get('pct', 0)
            
            index_rec = 'INDEX' if level['level'] <= 1 else ('SELECTIVE' if level['level'] == 2 else 'NOINDEX')
            index_color = 'var(--accent-green)' if index_rec == 'INDEX' else ('var(--accent-yellow)' if index_rec == 'SELECTIVE' else 'var(--accent-red)')
            
            level_rows += f"""
            <tr>
                <td><strong>N{level['level']}</strong></td>
                <td>{level.get('url_count', 0):,}</td>
                <td>{level.get('sessions', 0):,}</td>
                <td>{level.get('pct', 0):.1f}%</td>
                <td>{seo_sessions:,}</td>
                <td>{seo_pct:.1f}%</td>
                <td><span style="color: {index_color}; font-weight: 600;">{index_rec}</span></td>
            </tr>
            """
        
        # Generar visualización de arquitectura recomendada
        rec_arch = architecture.get('recommended_architecture', {})
        optimal_order = rec_arch.get('optimal_facet_order', ['size', 'brand', 'technology'])
        url_struct = rec_arch.get('url_structure', {})
        
        architecture_visual = ""
        levels_config = [
            ('N0', f'/{self.category}', 'Categoría', 'var(--accent-purple)', url_struct.get('N0', {}).get('pct', 0), 'INDEX'),
            ('N1', f'/{self.category}/{{faceta}}', optimal_order[0].upper() if optimal_order else 'FACET', 'var(--accent-green)', url_struct.get('N1', {}).get('pct', 0), 'INDEX'),
            ('N2', f'/{self.category}/{{f1}}/{{f2}}', f'{optimal_order[0].upper()}+{optimal_order[1].upper() if len(optimal_order) > 1 else "BRAND"}', 'var(--accent-yellow)', url_struct.get('N2', {}).get('pct', 0), 'SELECTIVE'),
            ('N3+', f'/{self.category}/{{f1}}/{{f2}}/{{f3}}...', 'Múltiples', 'var(--accent-red)', url_struct.get('N3+', {}).get('pct', 0), 'NOINDEX'),
        ]
        
        for level_name, pattern, desc, color, pct, index in levels_config:
            margin = {'N0': 0, 'N1': 2, 'N2': 4, 'N3+': 6}.get(level_name, 0)
            architecture_visual += f"""
            <div class="arch-level" style="margin-left: {margin}rem; border-left: 4px solid {color};">
                <div class="arch-badge" style="background: {color};">{level_name}</div>
                <div class="arch-content">
                    <div class="arch-pattern">{pattern}</div>
                    <div class="arch-desc">{desc} • {pct:.1f}% del tráfico</div>
                </div>
                <span class="arch-index" style="background: {'rgba(0,255,136,0.2)' if index == 'INDEX' else 'rgba(255,217,61,0.2)' if index == 'SELECTIVE' else 'rgba(255,107,107,0.2)'}; color: {color};">{index}</span>
            </div>
            """
        
        # Generar tabla de combinaciones N2
        n2_combos = architecture.get('n2_analysis', {}).get('facet_orders', [])
        combo_rows = ""
        for combo in n2_combos[:8]:
            combo_rows += f"""
            <tr>
                <td>{combo.get('order', '')}</td>
                <td>{combo.get('sessions', 0):,}</td>
                <td><span style="color: var(--accent-green);">✓ Indexar</span></td>
            </tr>
            """
        
        # Generar insights HTML
        arch_insights = [i for i in insights if i.get('category') == 'architecture'][:5]
        insights_html = ""
        for insight in arch_insights:
            priority_class = 'critical' if insight.get('priority') == 'HIGH' else ('important' if insight.get('priority') == 'MEDIUM' else '')
            insights_html += f"""
            <div class="recommendation {priority_class}">
                <div class="rec-number">{'!' if priority_class == 'critical' else '→'}</div>
                <div class="rec-content">
                    <h4>{insight.get('title', '')}</h4>
                    <p>{insight.get('description', '')}</p>
                    {f'<p style="margin-top: 0.5rem;"><strong>Acción:</strong> {insight.get("action", "")}</p>' if insight.get('action') else ''}
                </div>
            </div>
            """
        
        # SEO recommendations
        seo_recs = rec_arch.get('seo_recommendations', [])
        seo_recs_html = ""
        for i, rec in enumerate(seo_recs, 1):
            seo_recs_html += f"""
            <div style="display: flex; align-items: flex-start; gap: 1rem; padding: 1rem; background: var(--bg-secondary); border-radius: 8px; margin-bottom: 0.8rem;">
                <div style="width: 28px; height: 28px; background: var(--accent-cyan); color: #000; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; flex-shrink: 0;">{i}</div>
                <div style="font-size: 0.9rem;">{rec}</div>
            </div>
            """

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arquitectura de Facetas | {self.category.title()}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        {self._get_css_base()}
        .arch-level {{
            display: flex;
            align-items: center;
            padding: 1rem;
            background: var(--bg-card);
            border-radius: 12px;
            margin-bottom: 0.8rem;
        }}
        .arch-badge {{
            width: 45px;
            height: 45px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: #000;
            margin-right: 1rem;
            flex-shrink: 0;
        }}
        .arch-content {{ flex: 1; }}
        .arch-pattern {{
            font-family: monospace;
            color: var(--accent-cyan);
            font-size: 0.95rem;
        }}
        .arch-desc {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 0.2rem;
        }}
        .arch-index {{
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        .ux-seo-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-top: 1.5rem;
        }}
        .comparison-box {{
            padding: 1.5rem;
            border-radius: 12px;
        }}
        .comparison-box.ux {{
            background: linear-gradient(135deg, rgba(0,217,255,0.1), rgba(0,217,255,0.05));
            border: 1px solid rgba(0,217,255,0.2);
        }}
        .comparison-box.seo {{
            background: linear-gradient(135deg, rgba(0,255,136,0.1), rgba(0,255,136,0.05));
            border: 1px solid rgba(0,255,136,0.2);
        }}
        .comparison-box h4 {{
            margin-bottom: 1rem;
        }}
        .comparison-box.ux h4 {{ color: var(--accent-cyan); }}
        .comparison-box.seo h4 {{ color: var(--accent-green); }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🏗️ Arquitectura de Facetas</h1>
            <p>Análisis de niveles de navegación UX + visibilidad SEO</p>
            <span class="category">📦 {self.category.title()}</span>
        </header>
        
        <div class="metrics-row">
            <div class="metric-card">
                <div class="metric-icon">📊</div>
                <div class="metric-value">{self._format_number(architecture.get('total_sessions', metrics.get('total_internal_sessions', 0)))}</div>
                <div class="metric-label">Sesiones Totales</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">🔗</div>
                <div class="metric-value">{self._format_number(architecture.get('total_urls', metrics.get('total_urls', 0)))}</div>
                <div class="metric-label">URLs Analizadas</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">📐</div>
                <div class="metric-value">{len(optimal_order)}</div>
                <div class="metric-label">Facetas Principales</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">✅</div>
                <div class="metric-value">{rec_arch.get('indexable_percentage', 0):.0f}%</div>
                <div class="metric-label">Indexable</div>
            </div>
        </div>
        
        <!-- Arquitectura Visual -->
        <section class="section">
            <div class="section-title">
                <h2>🏛️ Arquitectura de URLs Recomendada</h2>
                <div class="section-line"></div>
            </div>
            
            <div class="cards-grid">
                <div class="card">
                    <h3>📐 Estructura de Niveles</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                        Basado en {self._format_number(architecture.get('total_sessions', 0))} sesiones de navegación real
                    </p>
                    <div style="background: var(--bg-secondary); border-radius: 16px; padding: 1.5rem;">
                        {architecture_visual}
                    </div>
                    <div class="insight-box" style="margin-top: 1rem;">
                        <h4>💡 Orden Óptimo de Facetas</h4>
                        <p style="font-size: 1.1rem; margin-top: 0.5rem;">
                            {' → '.join([f.upper() for f in optimal_order[:4]])}
                        </p>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📊 Distribución por Nivel (UX vs SEO)</h3>
                    <div class="chart-container">
                        <canvas id="levelChart"></canvas>
                    </div>
                </div>
            </div>
        </section>
        
        <!-- Tabla de Niveles -->
        <section class="section">
            <div class="section-title">
                <h2>📋 Detalle por Nivel de Profundidad</h2>
                <div class="section-line"></div>
            </div>
            
            <div class="card card-full">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Nivel</th>
                            <th>URLs</th>
                            <th>Sesiones UX</th>
                            <th>% UX</th>
                            <th>Sesiones SEO</th>
                            <th>% SEO</th>
                            <th>Indexación</th>
                        </tr>
                    </thead>
                    <tbody>
                        {level_rows}
                    </tbody>
                </table>
                
                <div class="ux-seo-comparison">
                    <div class="comparison-box ux">
                        <h4>🖱️ Navegación UX</h4>
                        <p>Cómo navegan los usuarios internamente por los filtros</p>
                        <ul style="margin-top: 1rem; padding-left: 1.5rem; color: var(--text-secondary);">
                            <li>N0-N1 concentran ~{(url_struct.get('N0', {}).get('pct', 0) + url_struct.get('N1', {}).get('pct', 0)):.0f}% del uso</li>
                            <li>Orden preferido: {' > '.join([f.title() for f in optimal_order[:3]])}</li>
                            <li>URLs con precio: usadas pero no indexables</li>
                        </ul>
                    </div>
                    <div class="comparison-box seo">
                        <h4>🔍 Visibilidad SEO</h4>
                        <p>Qué URLs deben ser rastreables e indexables</p>
                        <ul style="margin-top: 1rem; padding-left: 1.5rem; color: var(--text-secondary);">
                            <li><strong>INDEX:</strong> N0 y todas las N1</li>
                            <li><strong>SELECTIVE:</strong> N2 con volumen de búsqueda</li>
                            <li><strong>NOINDEX:</strong> N3+ y URLs con ?price</li>
                        </ul>
                    </div>
                </div>
            </div>
        </section>
        
        <!-- Combinaciones N2 -->
        <section class="section">
            <div class="section-title">
                <h2>🔗 Combinaciones N2 Más Usadas</h2>
                <div class="section-line"></div>
            </div>
            
            <div class="cards-grid">
                <div class="card">
                    <h3>🎯 Top Combinaciones para Indexar</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Combinación</th>
                                <th>Sesiones</th>
                                <th>Acción</th>
                            </tr>
                        </thead>
                        <tbody>
                            {combo_rows if combo_rows else '<tr><td colspan="3" style="text-align: center;">Sin datos de combinaciones N2</td></tr>'}
                        </tbody>
                    </table>
                </div>
                
                <div class="card">
                    <h3>📈 Recomendaciones SEO</h3>
                    {seo_recs_html if seo_recs_html else '<p style="color: var(--text-secondary);">Carga más datos para generar recomendaciones.</p>'}
                </div>
            </div>
        </section>
        
        <!-- Insights de Arquitectura -->
        <section class="section">
            <div class="section-title">
                <h2>💡 Insights de Arquitectura</h2>
                <div class="section-line"></div>
            </div>
            
            <div class="card card-full">
                {insights_html if insights_html else '<p style="color: var(--text-secondary);">No hay insights de arquitectura disponibles.</p>'}
            </div>
        </section>
        
        <footer class="footer">
            <p>Facet Architecture Report | {self.category.title()}</p>
            <p>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </footer>
    </div>
    
    <script>
        Chart.defaults.color = '#a0a0b0';
        
        // Level Distribution Chart
        const levelLabels = {level_labels};
        const levelUX = {level_ux_values};
        const levelSEO = {level_seo_values};
        
        new Chart(document.getElementById('levelChart'), {{
            type: 'bar',
            data: {{
                labels: levelLabels,
                datasets: [
                    {{ 
                        label: 'Sesiones UX', 
                        data: levelUX, 
                        backgroundColor: 'rgba(0,217,255,0.8)',
                        borderRadius: 4
                    }},
                    {{ 
                        label: 'Sesiones SEO', 
                        data: levelSEO.length > 0 ? levelSEO : levelUX.map(() => 0), 
                        backgroundColor: 'rgba(0,255,136,0.8)',
                        borderRadius: 4
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ 
                    legend: {{ position: 'top' }},
                    title: {{ display: true, text: 'Distribución de Sesiones por Nivel' }}
                }},
                scales: {{
                    x: {{ grid: {{ display: false }} }},
                    y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        return html
    
    def generate_market_share_report(self) -> str:
        """Genera el reporte de share de mercado por marca"""
        
        brand_data = self.data.get('brand_analysis', [])
        metrics = self.data.get('metrics', {})
        
        if not brand_data:
            return self._generate_empty_report("Market Share", "No hay datos de marcas disponibles")
        
        # Preparar datos para gráficos
        brand_labels = json.dumps([b.get('brand', '').title() for b in brand_data[:8]])
        brand_ux = json.dumps([b.get('internal_share', 0) for b in brand_data[:8]])
        brand_seo = json.dumps([b.get('seo_share', 0) for b in brand_data[:8]])
        
        # Generar cards de marcas
        brand_cards = ""
        medals = ['🥇', '🥈', '🥉', '', '', '', '', '']
        colors = ['#a50034', '#1428a0', '#ff6700', '#a855f7', '#e31e26', '#0066b3', '#00d9ff', '#ffd93d']
        
        for i, brand in enumerate(brand_data[:6]):
            gap = brand.get('internal_share', 0) - brand.get('seo_share', 0)
            gap_class = 'up' if gap > 0 else ('down' if gap < 0 else 'neutral')
            gap_symbol = '↑' if gap > 0 else ('↓' if gap < 0 else '≈')
            
            brand_cards += f"""
            <div class="brand-card" style="border-top: 4px solid {colors[i]};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div style="font-size: 1.3rem; font-weight: 700;">{medals[i]} {brand.get('brand', '').title()}</div>
                    <div style="font-size: 2rem; opacity: 0.3;">#{i+1}</div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem;">
                    <div style="text-align: center; padding: 0.8rem; background: rgba(0,0,0,0.2); border-radius: 8px;">
                        <div style="font-size: 1.4rem; font-weight: 700; color: var(--accent-cyan);">{brand.get('internal_share', 0):.1f}%</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Share UX</div>
                    </div>
                    <div style="text-align: center; padding: 0.8rem; background: rgba(0,0,0,0.2); border-radius: 8px;">
                        <div style="font-size: 1.4rem; font-weight: 700; color: var(--accent-green);">{brand.get('seo_share', 0):.1f}%</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Share SEO</div>
                    </div>
                    <div style="text-align: center; padding: 0.8rem; background: rgba(0,0,0,0.2); border-radius: 8px;">
                        <div style="font-size: 1.4rem; font-weight: 700;">{self._format_number(brand.get('internal_sessions', 0))}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Sesiones</div>
                    </div>
                </div>
                <div style="margin-top: 1rem;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-secondary);">
                        <span>Gap UX vs SEO</span>
                        <span style="color: var({'--accent-green' if gap > 0 else '--accent-red' if gap < 0 else '--accent-yellow'});">{gap_symbol} {abs(gap):.1f}%</span>
                    </div>
                    <div class="progress-bar" style="margin-top: 0.3rem;">
                        <div class="progress-fill" style="width: {brand.get('internal_share', 0) * 3}%; background: var(--accent-cyan);"></div>
                    </div>
                </div>
            </div>
            """
        
        # Generar tabla comparativa
        table_rows = ""
        for brand in brand_data[:10]:
            gap = brand.get('internal_share', 0) - brand.get('seo_share', 0)
            trend = '↑ Más UX' if gap > 1 else ('↓ Más SEO' if gap < -1 else '≈ Equilibrado')
            trend_class = 'color: var(--accent-green)' if gap > 1 else ('color: var(--accent-red)' if gap < -1 else 'color: var(--accent-yellow)')
            
            table_rows += f"""
            <tr>
                <td><strong>{brand.get('brand', '').title()}</strong></td>
                <td>{brand.get('internal_sessions', 0):,}</td>
                <td>{brand.get('internal_share', 0):.1f}%</td>
                <td>{brand.get('seo_sessions', 0):,.0f}</td>
                <td>{brand.get('seo_share', 0):.1f}%</td>
                <td>{gap:+.1f}%</td>
                <td><span style="{trend_class}">{trend}</span></td>
            </tr>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Share | {self.category.title()}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        {self._get_css_base()}
        .brand-card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🏆 Market Share por Marca</h1>
            <p>Análisis de posicionamiento basado en comportamiento real</p>
            <span class="category">📦 {self.category.title()}</span>
        </header>
        
        <section class="section">
            <div class="section-title">
                <h2>📊 Distribución de Interés</h2>
                <div class="section-line"></div>
            </div>
            
            <div class="cards-grid">
                <div class="card">
                    <h3>🥧 Share por Marca (Uso Interno)</h3>
                    <div class="chart-container">
                        <canvas id="shareChart"></canvas>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📈 Comparativa UX vs SEO</h3>
                    <div class="chart-container">
                        <canvas id="compChart"></canvas>
                    </div>
                </div>
            </div>
        </section>
        
        <section class="section">
            <div class="section-title">
                <h2>🏷️ Análisis por Marca</h2>
                <div class="section-line"></div>
            </div>
            
            <div class="cards-grid cards-grid-3">
                {brand_cards}
            </div>
        </section>
        
        <section class="section">
            <div class="section-title">
                <h2>📋 Tabla Comparativa</h2>
                <div class="section-line"></div>
            </div>
            
            <div class="card card-full">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Marca</th>
                            <th>Sesiones UX</th>
                            <th>Share UX</th>
                            <th>Sesiones SEO</th>
                            <th>Share SEO</th>
                            <th>Gap</th>
                            <th>Tendencia</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </section>
        
        <footer class="footer">
            <p>Market Share Report | {self.category.title()}</p>
            <p>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </footer>
    </div>
    
    <script>
        Chart.defaults.color = '#a0a0b0';
        
        const brandLabels = {brand_labels};
        const brandUX = {brand_ux};
        const brandSEO = {brand_seo};
        
        new Chart(document.getElementById('shareChart'), {{
            type: 'doughnut',
            data: {{
                labels: brandLabels.map((l, i) => l + ' (' + brandUX[i].toFixed(1) + '%)'),
                datasets: [{{
                    data: brandUX,
                    backgroundColor: ['#a50034', '#1428a0', '#ff6700', '#a855f7', '#e31e26', '#0066b3', '#00d9ff', '#444'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'right' }} }}
            }}
        }});
        
        new Chart(document.getElementById('compChart'), {{
            type: 'bar',
            data: {{
                labels: brandLabels,
                datasets: [
                    {{ label: 'Share UX (%)', data: brandUX, backgroundColor: 'rgba(0,217,255,0.8)', borderRadius: 4 }},
                    {{ label: 'Share SEO (%)', data: brandSEO, backgroundColor: 'rgba(0,255,136,0.8)', borderRadius: 4 }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ grid: {{ display: false }} }},
                    y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        return html
    
    def generate_content_strategy_report(self) -> str:
        """Genera el reporte de estrategia de contenido informacional ↔ transaccional"""
        
        cannibalization = self.data.get('cannibalization', [])
        content_mapping = self.data.get('content_mapping', [])
        metrics = self.data.get('metrics', {})
        
        # Generar mapeo artículo → filtro
        mapping_html = ""
        for item in content_mapping[:8]:
            mapping_html += f"""
            <div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 1rem; margin-bottom: 0.8rem; align-items: center;">
                <div style="padding: 1rem; background: var(--bg-card); border-radius: 8px; border-left: 3px solid var(--accent-purple);">
                    <div style="font-family: monospace; color: var(--accent-cyan); font-size: 0.8rem;">{item.get('article_url', '')}</div>
                    <div style="color: var(--accent-yellow); font-size: 0.85rem; margin-top: 0.3rem;">Query: "{item.get('query', '')}"</div>
                </div>
                <div style="font-size: 1.5rem; color: var(--accent-cyan);">→</div>
                <div style="padding: 1rem; background: var(--bg-card); border-radius: 8px; border-left: 3px solid var(--accent-green);">
                    <div style="font-family: monospace; color: var(--accent-cyan); font-size: 0.8rem;">{item.get('target_filter', '')}</div>
                    <div style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 0.3rem;">{item.get('clicks', 0)} clics/mes</div>
                </div>
            </div>
            """
        
        # Generar casos de canibalización
        cannibalization_html = ""
        for item in cannibalization[:10]:
            priority_class = 'high' if item.get('priority') == 'HIGH' else ('medium' if item.get('priority') == 'MEDIUM' else 'low')
            cannibalization_html += f"""
            <tr>
                <td>{item.get('query', '')}</td>
                <td style="font-family: monospace; font-size: 0.8rem;">{item.get('ranking_url', '')[:50]}...</td>
                <td style="font-family: monospace; font-size: 0.8rem;">{item.get('target_url', '')}</td>
                <td>{item.get('clicks', 0)}</td>
                <td><span class="badge {priority_class}">{item.get('priority', 'LOW')}</span></td>
            </tr>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Strategy | {self.category.title()}</title>
    <style>
        {self._get_css_base()}
        .flow-stage {{
            flex: 1;
            padding: 2rem;
            background: var(--bg-card);
            border-radius: 16px;
            text-align: center;
        }}
        .flow-stage.info {{ border-top: 4px solid var(--accent-purple); }}
        .flow-stage.trans {{ border-top: 4px solid var(--accent-green); }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📝 Content Strategy</h1>
            <p>Entrelazado entre Contenido Informacional y Filtros Transaccionales</p>
            <span class="category">📦 {self.category.title()}</span>
        </header>
        
        <section class="section">
            <div class="section-title">
                <h2>🔄 Flujo del Usuario</h2>
                <div class="section-line"></div>
            </div>
            
            <div style="display: flex; gap: 1rem; align-items: stretch;">
                <div class="flow-stage info">
                    <div style="font-size: 3rem;">📚</div>
                    <h3>Contenido Informacional</h3>
                    <p style="color: var(--text-secondary);">Guías, comparativas, reviews</p>
                    <div style="font-size: 2rem; font-weight: 700; color: var(--accent-purple); margin-top: 1rem;">
                        {metrics.get('articles_count', 0)}
                    </div>
                    <div style="color: var(--text-secondary);">Artículos</div>
                </div>
                
                <div style="display: flex; align-items: center; font-size: 2rem; color: var(--accent-cyan);">→</div>
                
                <div style="padding: 2rem; text-align: center;">
                    <div style="font-size: 2rem;">🔗</div>
                    <div style="font-weight: 600; color: var(--accent-cyan);">CTA</div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.5rem;">
                        "Ver todos los productos →"
                    </div>
                </div>
                
                <div style="display: flex; align-items: center; font-size: 2rem; color: var(--accent-cyan);">→</div>
                
                <div class="flow-stage trans">
                    <div style="font-size: 3rem;">🛒</div>
                    <h3>Filtros Transaccionales</h3>
                    <p style="color: var(--text-secondary);">Listados de productos</p>
                    <div style="font-size: 2rem; font-weight: 700; color: var(--accent-green); margin-top: 1rem;">
                        {metrics.get('filters_count', 0)}
                    </div>
                    <div style="color: var(--text-secondary);">Filtros</div>
                </div>
            </div>
        </section>
        
        <section class="section">
            <div class="section-title">
                <h2>🗺️ Mapeo Artículos → Filtros</h2>
                <div class="section-line"></div>
            </div>
            
            <div class="card card-full">
                {mapping_html if mapping_html else '<p style="color: var(--text-secondary);">No hay datos de mapeo disponibles.</p>'}
            </div>
        </section>
        
        <section class="section">
            <div class="section-title">
                <h2>⚠️ Casos de Canibalización</h2>
                <div class="section-line"></div>
            </div>
            
            <div class="card card-full">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Query</th>
                            <th>URL Ranking</th>
                            <th>Debería ir a</th>
                            <th>Clics</th>
                            <th>Prioridad</th>
                        </tr>
                    </thead>
                    <tbody>
                        {cannibalization_html if cannibalization_html else '<tr><td colspan="5" style="text-align: center; color: var(--text-secondary);">No hay casos de canibalización detectados</td></tr>'}
                    </tbody>
                </table>
            </div>
        </section>
        
        <footer class="footer">
            <p>Content Strategy Report | {self.category.title()}</p>
            <p>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </footer>
    </div>
</body>
</html>"""
        
        return html
    
    def generate_executive_summary(self) -> str:
        """Genera un resumen ejecutivo con todos los insights clave"""
        
        insights = self.data.get('insights', [])
        metrics = self.data.get('metrics', {})
        facet_usage = self.data.get('facet_usage', {})
        brand_data = self.data.get('brand_analysis', [])
        
        # Insights HTML
        insights_html = ""
        for i, insight in enumerate(insights[:10]):
            priority_class = 'critical' if insight.get('priority') == 'HIGH' else ('important' if insight.get('priority') == 'MEDIUM' else 'success')
            insights_html += f"""
            <div class="recommendation {priority_class}">
                <div class="rec-number">{i+1}</div>
                <div class="rec-content">
                    <h4>{insight.get('title', '')}</h4>
                    <p>{insight.get('description', '')}</p>
                    {'<p style="margin-top: 0.5rem;"><strong>Acción:</strong> ' + insight.get('action', '') + '</p>' if insight.get('action') else ''}
                </div>
            </div>
            """
        
        # Top facetas
        facet_order = sorted(facet_usage.items(), key=lambda x: -x[1].get('sessions_all', 0))[:5]
        facet_html = ""
        for facet, data in facet_order:
            if facet not in ['total', 'other']:
                facet_html += f"""
                <div style="display: flex; justify-content: space-between; padding: 0.8rem; background: var(--bg-secondary); border-radius: 8px; margin-bottom: 0.5rem;">
                    <span style="font-weight: 600;">{facet.replace('_', ' ').title()}</span>
                    <span style="color: var(--accent-cyan);">{data.get('pct_all', 0):.1f}%</span>
                </div>
                """
        
        # Top marcas
        brand_html = ""
        for brand in brand_data[:5]:
            brand_html += f"""
            <div style="display: flex; justify-content: space-between; padding: 0.8rem; background: var(--bg-secondary); border-radius: 8px; margin-bottom: 0.5rem;">
                <span style="font-weight: 600;">{brand.get('brand', '').title()}</span>
                <span style="color: var(--accent-green);">{brand.get('internal_share', 0):.1f}%</span>
            </div>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resumen Ejecutivo | {self.category.title()}</title>
    <style>
        {self._get_css_base()}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📋 Resumen Ejecutivo</h1>
            <p>Insights clave y recomendaciones priorizadas</p>
            <span class="category">📦 {self.category.title()}</span>
        </header>
        
        <div class="metrics-row">
            <div class="metric-card">
                <div class="metric-icon">📊</div>
                <div class="metric-value">{self._format_number(metrics.get('total_internal_sessions', 0))}</div>
                <div class="metric-label">Sesiones Internas</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">🔍</div>
                <div class="metric-value">{metrics.get('seo_ratio', 0):.0f}%</div>
                <div class="metric-label">Ratio SEO</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">🏷️</div>
                <div class="metric-value">{len(brand_data)}</div>
                <div class="metric-label">Marcas Activas</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">💡</div>
                <div class="metric-value">{len(insights)}</div>
                <div class="metric-label">Insights Detectados</div>
            </div>
        </div>
        
        <section class="section">
            <div class="section-title">
                <h2>💡 Insights Clave</h2>
                <div class="section-line"></div>
            </div>
            
            <div class="card card-full">
                {insights_html if insights_html else '<p style="color: var(--text-secondary);">Carga más datos para generar insights automáticos.</p>'}
            </div>
        </section>
        
        <div class="cards-grid">
            <div class="card">
                <h3>📐 Orden Óptimo de Facetas</h3>
                {facet_html if facet_html else '<p style="color: var(--text-secondary);">Sin datos de facetas.</p>'}
            </div>
            
            <div class="card">
                <h3>🏆 Top Marcas</h3>
                {brand_html if brand_html else '<p style="color: var(--text-secondary);">Sin datos de marcas.</p>'}
            </div>
        </div>
        
        <footer class="footer">
            <p>Executive Summary | {self.category.title()}</p>
            <p>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </footer>
    </div>
</body>
</html>"""
        
        return html
    
    def _generate_empty_report(self, title: str, message: str) -> str:
        """Genera un reporte vacío con mensaje"""
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{title} | {self.category.title()}</title>
    <style>{self._get_css_base()}</style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>{title}</h1>
            <span class="category">📦 {self.category.title()}</span>
        </header>
        <div class="card card-full" style="text-align: center; padding: 3rem;">
            <p style="color: var(--text-secondary); font-size: 1.2rem;">{message}</p>
            <p style="color: var(--text-secondary); margin-top: 1rem;">Carga los archivos necesarios para generar este reporte.</p>
        </div>
    </div>
</body>
</html>"""
