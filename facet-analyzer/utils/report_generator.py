"""
Generador de Reportes HTML - v2
Reportes con información de valor real
"""
from typing import Dict, Any
from datetime import datetime
import pandas as pd


class ReportGenerator:
    """Genera reportes HTML con información de valor"""
    
    def __init__(self, category: str, data: Dict[str, Any]):
        self.category = category
        self.data = data
    
    def _fmt(self, num: float) -> str:
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        return f"{num:,.0f}"
    
    def _css(self) -> str:
        return """
        :root {
            --bg: #0f172a;
            --card: #1e293b;
            --border: #334155;
            --cyan: #22d3ee;
            --green: #4ade80;
            --yellow: #facc15;
            --red: #f87171;
            --text: #f1f5f9;
            --muted: #94a3b8;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 3rem 2rem;
            background: linear-gradient(135deg, rgba(34,211,238,0.1), rgba(74,222,128,0.1));
            border-radius: 20px;
            margin-bottom: 2rem;
            border: 1px solid var(--border);
        }
        .header h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, var(--cyan), var(--green));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .header p { color: var(--muted); }
        .metrics {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .metric {
            background: var(--card);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid var(--border);
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--cyan);
        }
        .metric-label {
            color: var(--muted);
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }
        .card {
            background: var(--card);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border);
        }
        .card h2 {
            color: var(--cyan);
            font-size: 1.3rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
        }
        .card h3 {
            color: var(--text);
            font-size: 1.1rem;
            margin: 1rem 0 0.5rem 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        th, td {
            padding: 0.8rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        th {
            background: rgba(34,211,238,0.1);
            color: var(--cyan);
            font-size: 0.85rem;
            text-transform: uppercase;
        }
        td { color: var(--text); }
        .tag {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .tag-green { background: rgba(74,222,128,0.2); color: var(--green); }
        .tag-yellow { background: rgba(250,204,21,0.2); color: var(--yellow); }
        .tag-red { background: rgba(248,113,113,0.2); color: var(--red); }
        .level-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin: 1rem 0;
        }
        .level-box {
            text-align: center;
            padding: 1.5rem;
            border-radius: 12px;
            background: var(--bg);
            border: 2px solid;
        }
        .level-box.n0 { border-color: var(--green); }
        .level-box.n1 { border-color: var(--cyan); }
        .level-box.n2 { border-color: var(--yellow); }
        .level-box.n3 { border-color: var(--red); }
        .level-name { font-size: 1.5rem; font-weight: 700; }
        .level-pct { font-size: 2rem; font-weight: 700; margin: 0.5rem 0; }
        .insight-box {
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            border-left: 4px solid;
        }
        .insight-high { background: rgba(248,113,113,0.1); border-color: var(--red); }
        .insight-medium { background: rgba(250,204,21,0.1); border-color: var(--yellow); }
        .footer {
            text-align: center;
            padding: 2rem;
            color: var(--muted);
            margin-top: 2rem;
        }
        """
    
    def generate_executive_summary(self) -> str:
        metrics = self.data.get('metrics', {})
        insights = self.data.get('insights', [])
        sources = self.data.get('data_sources', [])
        arch = self.data.get('architecture', {})
        rec = arch.get('recommended_architecture', {})
        url_struct = rec.get('url_structure', {})
        
        # Insights HTML
        insights_html = ""
        for ins in insights[:10]:
            priority = ins.get('priority', 'LOW')
            cls = 'insight-high' if priority == 'HIGH' else 'insight-medium' if priority == 'MEDIUM' else ''
            icon = '🔴' if priority == 'HIGH' else '🟡' if priority == 'MEDIUM' else '🟢'
            insights_html += f"""
            <div class="insight-box {cls}">
                <strong>{icon} {ins.get('title', '')}</strong>
                <p style="color: var(--muted); margin-top: 0.3rem;">{ins.get('description', '')}</p>
            </div>
            """
        
        # Sources HTML
        sources_html = " • ".join([f"✅ {s}" for s in sources]) if sources else "Sin datos cargados"
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resumen Ejecutivo | {self.category.title()}</title>
    <style>{self._css()}</style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📋 Resumen Ejecutivo</h1>
            <p>{self.category.title()} | Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </header>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{self._fmt(metrics.get('total_internal_sessions', 0))}</div>
                <div class="metric-label">Demanda Interna</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.get('seo_ratio', 0):.0f}%</div>
                <div class="metric-label">Ratio SEO</div>
            </div>
            <div class="metric">
                <div class="metric-value">{self._fmt(metrics.get('total_urls', 0))}</div>
                <div class="metric-label">URLs Analizadas</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(insights)}</div>
                <div class="metric-label">Insights</div>
            </div>
        </div>
        
        <div class="card">
            <h2>📂 Fuentes de Datos</h2>
            <p>{sources_html}</p>
        </div>
        
        <div class="card">
            <h2>💡 Insights Clave</h2>
            {insights_html if insights_html else '<p style="color: var(--muted);">Sin insights disponibles</p>'}
        </div>
        
        <div class="card">
            <h2>🎯 Recomendaciones Principales</h2>
            <ul style="color: var(--text); padding-left: 1.5rem;">
                <li>Indexar todas las URLs N0 y N1 (categoría + un atributo)</li>
                <li>Evaluar N2 por demanda de mercado (>200 búsquedas/mes)</li>
                <li>NOINDEX para N3+ y URLs con parámetros</li>
                <li>Resolver casos de canibalización de alto impacto</li>
            </ul>
        </div>
        
        <footer class="footer">
            <p>Facet Architecture Analyzer | {self.category.title()}</p>
        </footer>
    </div>
</body>
</html>"""
    
    def generate_architecture_report(self) -> str:
        arch = self.data.get('architecture', {})
        rec = arch.get('recommended_architecture', {})
        url_struct = rec.get('url_structure', {})
        optimal_order = rec.get('optimal_facet_order', [])
        
        n0 = url_struct.get('N0', {}).get('pct', 5)
        n1 = url_struct.get('N1', {}).get('pct', 45)
        n2 = url_struct.get('N2', {}).get('pct', 35)
        n3 = url_struct.get('N3+', {}).get('pct', 15)
        
        # Facet order
        order_html = " → ".join([f"<strong>{f.upper()}</strong>" for f in optimal_order[:5]]) if optimal_order else "Sin datos"
        
        # Navigation data
        nav = self.data.get('navigation_system', {})
        layer1 = nav.get('layer1_ux', {})
        facets = layer1.get('facets', [])
        
        facets_html = ""
        for f in facets[:6]:
            facets_html += f"""
            <tr>
                <td><strong>{f.get('icon', '')} {f.get('name', '')}</strong></td>
                <td>{f.get('usage_pct', 0):.1f}%</td>
                <td>{'✅ Sí' if f.get('generates_url', True) else '❌ No'}</td>
                <td style="color: var(--muted);">{f.get('description', '')[:50]}...</td>
            </tr>
            """
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arquitectura | {self.category.title()}</title>
    <style>{self._css()}</style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🏗️ Arquitectura de Facetas</h1>
            <p>{self.category.title()} | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </header>
        
        <div class="card">
            <h2>📊 Distribución por Niveles</h2>
            <div class="level-grid">
                <div class="level-box n0">
                    <div class="level-name" style="color: var(--green);">N0</div>
                    <div style="color: var(--muted); font-size: 0.8rem;">/{self.category}</div>
                    <div class="level-pct" style="color: var(--green);">{n0:.0f}%</div>
                    <span class="tag tag-green">INDEX</span>
                </div>
                <div class="level-box n1">
                    <div class="level-name" style="color: var(--cyan);">N1</div>
                    <div style="color: var(--muted); font-size: 0.8rem;">/{self.category}/{{faceta}}</div>
                    <div class="level-pct" style="color: var(--cyan);">{n1:.0f}%</div>
                    <span class="tag tag-green">INDEX</span>
                </div>
                <div class="level-box n2">
                    <div class="level-name" style="color: var(--yellow);">N2</div>
                    <div style="color: var(--muted); font-size: 0.8rem;">/{self.category}/{{f1}}/{{f2}}</div>
                    <div class="level-pct" style="color: var(--yellow);">{n2:.0f}%</div>
                    <span class="tag tag-yellow">SELECTIVO</span>
                </div>
                <div class="level-box n3">
                    <div class="level-name" style="color: var(--red);">N3+</div>
                    <div style="color: var(--muted); font-size: 0.8rem;">3+ atributos</div>
                    <div class="level-pct" style="color: var(--red);">{n3:.0f}%</div>
                    <span class="tag tag-red">NOINDEX</span>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>🎯 Orden Óptimo de Facetas</h2>
            <p style="font-size: 1.2rem; margin: 1rem 0;">{order_html}</p>
            <p style="color: var(--muted);">Basado en demanda interna (uso de filtros por usuarios)</p>
        </div>
        
        <div class="card">
            <h2>🧭 Sistema de Navegación</h2>
            <table>
                <thead>
                    <tr>
                        <th>Faceta</th>
                        <th>Uso</th>
                        <th>Genera URL</th>
                        <th>Descripción</th>
                    </tr>
                </thead>
                <tbody>
                    {facets_html if facets_html else '<tr><td colspan="4" style="color: var(--muted);">Sin datos de facetas</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>📑 Reglas de Indexación</h2>
            <table>
                <thead>
                    <tr><th>Patrón</th><th>Acción</th><th>Condición</th></tr>
                </thead>
                <tbody>
                    <tr><td>/{self.category}</td><td><span class="tag tag-green">INDEX</span></td><td>Siempre - 500+ palabras</td></tr>
                    <tr><td>/{self.category}/{{tamaño}}</td><td><span class="tag tag-green">INDEX</span></td><td>Todos los tamaños - 150 palabras</td></tr>
                    <tr><td>/{self.category}/{{marca}}</td><td><span class="tag tag-green">INDEX</span></td><td>Si demanda >50 clics</td></tr>
                    <tr><td>/{self.category}/{{tech}}</td><td><span class="tag tag-green">INDEX</span></td><td>Tech diferenciadas (no /4k, /led)</td></tr>
                    <tr><td>/{self.category}/{{f1}}/{{f2}}</td><td><span class="tag tag-yellow">SELECTIVO</span></td><td>Si KW >200 ó clics >500</td></tr>
                    <tr><td>3+ atributos</td><td><span class="tag tag-red">NOINDEX</span></td><td>Canonical → padre N2</td></tr>
                    <tr><td>?order=, ?page=</td><td><span class="tag tag-red">NOINDEX</span></td><td>Canonical → sin parámetro</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>❌ URLs a NO INDEXAR</h2>
            <h3>3+ Atributos</h3>
            <p style="color: var(--muted);">/55/oled/lg, /65/samsung/qled → canonical al mejor padre N2</p>
            
            <h3>Parámetros</h3>
            <p style="color: var(--muted);">?order=price, ?page=2 → canonical sin parámetro</p>
            
            <h3>Redundantes</h3>
            <p style="color: var(--muted);">/4k (95% productos), /hdr, /wifi, /led → no diferencian</p>
        </div>
        
        <footer class="footer">
            <p>Facet Architecture Analyzer | {self.category.title()}</p>
        </footer>
    </div>
</body>
</html>"""
    
    def generate_market_share_report(self) -> str:
        brand_data = self.data.get('brand_analysis', [])
        
        rows = ""
        for b in brand_data[:15]:
            gap = b.get('gap', 0)
            gap_cls = 'tag-green' if gap > 0 else 'tag-red' if gap < -3 else ''
            rows += f"""
            <tr>
                <td><strong>{b.get('brand', '').title()}</strong></td>
                <td>{b.get('internal_share', 0):.1f}%</td>
                <td>{b.get('seo_share', 0):.1f}%</td>
                <td><span class="tag {gap_cls}">{gap:+.1f}%</span></td>
            </tr>
            """
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Market Share | {self.category.title()}</title>
    <style>{self._css()}</style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🏆 Market Share por Marca</h1>
            <p>{self.category.title()} | {datetime.now().strftime('%Y-%m-%d')}</p>
        </header>
        
        <div class="card">
            <h2>📊 Ranking de Marcas</h2>
            <table>
                <thead>
                    <tr><th>Marca</th><th>Demanda Interna</th><th>Demanda SEO</th><th>Gap</th></tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="4">Sin datos</td></tr>'}
                </tbody>
            </table>
            <p style="color: var(--muted); margin-top: 1rem; font-size: 0.85rem;">
                Gap positivo = más demanda interna que SEO (oportunidad de visibilidad)
            </p>
        </div>
        
        <footer class="footer">
            <p>Facet Architecture Analyzer</p>
        </footer>
    </div>
</body>
</html>"""
