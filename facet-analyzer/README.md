# 🏗️ Facet Architecture Analyzer

Herramienta de análisis **UX + SEO** para arquitectura de navegación facetada en ecommerce.

## 🎯 Objetivo Principal

Cruzar datos de **comportamiento interno** (cómo navegan los usuarios) con **demanda externa** (qué buscan en Google) para:

1. **Optimizar UX**: Ordenar facetas según uso real
2. **Maximizar SEO**: Indexar solo URLs con demanda
3. **Eliminar canibalización**: Que artículos no roben tráfico a filtros
4. **Detectar gaps**: Keywords sin filtro dedicado

## 📊 Análisis que realiza

| Análisis | Fuente de Datos | Insight |
|----------|-----------------|---------|
| **Orden de facetas** | Uso de filtros (Analytics) | Qué facetas usar primero en UI |
| **Matriz UX+SEO** | Analytics + GSC | Facetas con alto uso pero baja visibilidad |
| **Canibalización** | Top Query por URL | Artículos rankeando para queries transaccionales |
| **Gaps de demanda** | Keyword Research | Keywords sin filtro dedicado |
| **Reglas indexación** | Top Query | Qué URLs indexar/bloquear |

## 🚀 Despliegue

### Streamlit Cloud (Recomendado)

1. Fork este repositorio
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu GitHub y selecciona el repo
4. Main file: `app.py`

### Local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📁 Archivos de Entrada

| Archivo | Formato | Obligatorio | Descripción |
|---------|---------|-------------|-------------|
| **Top Query** | CSV (UTF-8) | ✅ Sí | BigQuery/GSC con `url`, `url_total_clicks`, `top_query` |
| **Uso Filtros** | CSV (Adobe) | Recomendado | Export de Analytics (ver formatos abajo) |
| **GSC Consultas** | CSV (español) | Opcional | Export de Search Console - Consultas |
| **GSC Páginas** | CSV (español) | Opcional | Export de Search Console - Páginas |
| **Keyword Research** | CSV/TSV (UTF-16) | Opcional | Export de Google Keyword Planner |

### Formatos de Uso de Filtros (Adobe Analytics)

La herramienta soporta **2 formatos** de export de Adobe Analytics:

#### 1. Search Filters (Recomendado)
Formato: `faceta:valor,sesiones`

```csv
#=================================================================
# Uso Filtros/Familias - Home Entertainment
#=================================================================
,Televisores
,Visits
Search Filters,1015093
pulgadas:55 pulgadas,83429
pulgadas:65 pulgadas,80506
marcas:lg,64556
marcas:samsung,61118
conectividad:smart tv,44992
order:price_asc,27783
tipo pantalla:oled,26560
```

**Facetas soportadas:**
| Faceta Adobe | Mapeo Interno |
|--------------|---------------|
| pulgadas / tamanho em polegadas | size |
| marcas | brand |
| tipo pantalla / tipo de painel | technology |
| conectividad / conectividade | connectivity |
| resolucion / resolução | resolution |
| frecuencia de refresco | refresh_rate |
| order | sorting |
| price | price |
| estado del articulo | condition |

#### 2. Page Full URL
Formato: URLs completas con sesiones

```csv
#=================================================================
# Uso Filtros/Familias - Home Entertainment
#=================================================================
,Televisores
,Visits
Page Full URL,1237795
(Low Traffic),697119
Unspecified,473460
https://www.pccomponentes.com/televisores,154105
https://www.pccomponentes.com/televisores/55-pulgadas,45379
https://www.pccomponentes.com/televisores/65-pulgadas,44004
https://www.pccomponentes.com/televisores/oled,16527
```

**Nota:** "(Low Traffic)" y "Unspecified" se ignoran automáticamente.

## 🔑 API Keys (Opcional)

Para validación con **doble pasada crítica**:

### Metodología de Validación IA

```
┌─────────────────────────────────────────────────────────────────┐
│  PASADA 1: Análisis Inicial                                     │
│  ────────────────────────────                                   │
│  - Claude/GPT analiza los datos                                 │
│  - Detecta canibalizaciones, gaps, problemas                    │
│  - Genera primera versión de recomendaciones                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PASADA 2: Crítica                                              │
│  ─────────────────                                              │
│  - Segunda IA (o segunda pasada) revisa el análisis             │
│  - Identifica errores, falsos positivos, omisiones              │
│  - Cuestiona asunciones y prioridades                           │
│  - Propone correcciones específicas                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PASADA 3: Refinamiento                                         │
│  ───────────────────────                                        │
│  - Aplica correcciones al análisis original                     │
│  - Marca falsos positivos detectados                            │
│  - Ajusta prioridades según crítica                             │
│  - Resultado final con alta confianza                           │
└─────────────────────────────────────────────────────────────────┘
```

### Configuración

- **Solo Anthropic**: Claude hace análisis Y crítica (self-critique)
- **Solo OpenAI**: GPT hace análisis Y crítica (self-critique)  
- **Ambas APIs**: Claude analiza → GPT critica (o viceversa)

La combinación de ambas APIs ofrece mayor diversidad de perspectivas.

## 📐 Arquitectura de Facetas

La app implementa estas reglas:

### Orden de Facetas en URL
```
/categoria/{tamaño}/{tecnología}/{marca}
```
Basado en comportamiento real: Tamaño (40%) > Marca (20%) > Tecnología (4%)

### Reglas de Indexación
| Nivel | Ejemplo | Indexar |
|-------|---------|---------|
| N1 | `/televisores/55-pulgadas` | ✅ Siempre |
| N2 | `/televisores/55-pulgadas/oled` | ⚠️ Si demanda >200 |
| N3+ | `/televisores/55-pulgadas/oled/samsung` | ❌ Canonical a N2 |
| Sorting | `?order=price` | ❌ Canonical sin param |
| Precio | `?precio=100-500` | ❌ Usar AJAX |

### Intención de Búsqueda
- **TRANSACCIONAL** → Filtro: "tv 55 pulgadas"
- **INFORMACIONAL** → Artículo: "mejor tv 55 pulgadas"

## 📈 Output

- **Resumen ejecutivo** con métricas clave
- **Matriz UX+SEO** interactiva
- **Lista de canibalizaciones** con filtro sugerido
- **Gaps de demanda** priorizados
- **Recomendaciones** ordenadas por impacto
- **Exportación** a CSV/JSON

## 🔒 Privacidad

- Los datos NO se envían a servidores externos
- Las API keys se usan solo en sesión
- Todo el procesamiento es local
