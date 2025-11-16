# Visualization Review: Geo-Equity Index Dashboard

## Executive Summary

The Geo-Equity Index Dashboard represents a comprehensive interactive geospatial visualization platform that synthesizes environmental, health, and socioeconomic data into an accessible web-based interface. Built entirely in Python using the Dash framework and Plotly visualization library, the application enables users to explore neighborhood-level health risk scores while simultaneously viewing nearby EPA-designated hazardous sites. This document provides an overview of the visualization strategies, design innovations, and implementation challenges encountered during development.

---

## Technology Stack Overview

The dashboard leverages a modern Python-based technology stack specifically chosen for its balance of rapid development capabilities and robust geospatial processing:

**Plotly** serves as the primary visualization engine, providing declarative chart generation with minimal boilerplate code. Unlike traditional JavaScript mapping libraries, Plotly enables pure-Python development, eliminating the context-switching between languages that typically burdens full-stack web applications.

**Dash** functions as the web framework layer, built atop Flask for server-side operations and React for client-side reactivity. Dash's callback system enables dynamic user interactions without requiring explicit JavaScript coding—a significant advantage for data science teams lacking front-end expertise. The entire user interface is constructed using Dash's HTML component library, which provides Python representations of standard HTML elements (Div, H1-H5, P, Button, Table, etc.). These components are written in Python but render as actual HTML in the browser, allowing developers to build complete web interfaces without writing raw HTML strings. This is a core feature of Dash that maintains the pure-Python development paradigm throughout the entire application stack.

**GeoPandas** handles geospatial data operations, extending the familiar Pandas DataFrame structure with geometric capabilities. The library processes GeoPackage files containing approximately 73,000 U.S. census tract polygons, performing spatial queries to determine which tracts fall within user-defined search radii.

**Shapely** provides computational geometry functions, most critically the Point-in-Polygon algorithm that identifies which census tract contains a user's search address. This enables instant retrieval of GEI scores without requiring manual tract selection.

**Geopy** interfaces with OpenStreetMap's Nominatim geocoding service via HTTP API calls (free but rate limited), converting human-readable addresses into latitude-longitude coordinates. Each address lookup queries Nominatim's remote servers, which return geographic coordinates and formatted address strings. An in-memory caching system stores previously geocoded addresses, reducing redundant API calls and improving response times for repeated searches while respecting Nominatim's rate limiting policies.

The deployment stack includes **Gunicorn** as a production-grade WSGI server and **Docker** for containerization, ensuring consistent behavior across development and production environments. The application can be deployed to cloud platforms like Heroku or AWS with minimal configuration changes.

---

## Visual Design Philosophy

The dashboard employs a layered visualization strategy, compositing multiple data representations onto a single map canvas. This approach mirrors traditional cartographic principles where base maps provide geographic context while thematic overlays communicate analytical insights.

### Layer 1: Census Tract Choropleth

The foundational visualization layer displays census tracts as colored polygons, with hue intensity representing GEI overall scores. The design employs a reversed Red-Yellow-Green diverging color scale, adhering to universal conventions where green signifies favorable conditions and red indicates concern. Unlike typical choropleth implementations that normalize colors per viewport, this application maintains a global color scale—meaning a tract's color remains constant regardless of zoom level or search location. This design decision prioritizes cross-region comparability over local contrast maximization.

The choropleth uses semi-transparent fills (60% opacity) to allow underlying basemap features to remain partially visible, preventing complete occlusion of street networks and geographic landmarks. White borders delineate individual tract boundaries, ensuring visual separation even when adjacent tracts share similar GEI scores.

### Layer 2: CIMC Hazard Site Markers

Environmental hazard sites appear as circular markers with a distinctive two-layer rendering approach. Each site consists of a black outline circle slightly larger than the colored interior, creating a "halo" effect that ensures visibility against both light and dark backgrounds. The interior circles employ a Yellow-Orange-Red sequential color scale to represent hazard severity scores ranging from 0 (minimal) to 6 (severe).

Marker size remains constant regardless of zoom level—a deliberate choice to maintain visual consistency. Alternative designs using scale-dependent sizing were tested but proved disorienting during zoom transitions, as markers would appear to "grow" or "shrink" unpredictably.

### Layer 3: Search Location Indicator

The user's queried address appears as a multi-layer concentric circle pattern—a "bullseye" design with five nested rings decreasing in size from outer to inner. Ring colors progress from blue through purple to magenta, with transparency gradually increasing toward the perimeter. This design creates a visually prominent focal point that remains distinguishable even when overlapping with dense CIMC site clusters or complex census tract boundaries.

The bullseye's prominence addresses a critical usability challenge: in busy map regions with numerous overlapping elements, users often struggled to relocate their original search point. The high-contrast, multi-ring design ensures the search location never becomes "lost" in visual clutter.

---

## Interactive Features

### Address Search and Geocoding

Users initiate map queries by entering free-text addresses into a prominent search bar. The geocoding system translates these inputs into geographic coordinates via the Nominatim API, with automatic validation and error messaging for ambiguous or invalid addresses. Successful geocodes trigger multiple simultaneous operations: the map centers and zooms to frame the search area appropriately, nearby CIMC sites are filtered by distance, census tracts within a buffered radius are selected, and the search location's specific GEI scores are retrieved via spatial join.

The system implements intelligent zoom calculation, automatically determining the optimal zoom level to display 1.5 times the user-specified search radius. This ensures the map frame provides sufficient context beyond the exact search area, allowing users to perceive neighboring tracts and identify spatial trends.

### Radius-Based Filtering

A slider control enables users to adjust the CIMC site search radius from 0 to 25 miles, with real-time map updates reflecting the new selection. Distance calculations employ the haversine formula rather than simple Euclidean distance, accounting for Earth's curvature to provide accurate geodesic measurements. This distinction becomes particularly significant at larger radii where flat-Earth approximations introduce substantial error.

The census tract selection uses a slightly different approach, applying a bounding box query with 20% buffer beyond the specified radius. This ensures tracts partially intersecting the search circle are included rather than requiring full containment—a design choice that prevents artificial "empty" zones at radius boundaries.

### Basemap Style Selector

Three basemap rendering modes address the performance-versus-detail tradeoff inherent in web mapping applications:

**No Basemap** mode eliminates tile loading entirely, displaying only census tract polygons, CIMC markers, and the search indicator against a white background. This fastest-loading option suits users prioritizing data layer visibility over geographic context, reducing initial render time to under one second even with thousands of census tracts.

**Light Basemap** mode uses the Carto Positron style—a simplified, fast-loading map emphasizing roads and boundaries without satellite imagery or terrain shading. This balanced option provides sufficient geographic context for orientation while maintaining responsive pan and zoom interactions.

**Detailed Basemap** mode defaults to OpenStreetMap tiles, offering complete street-level detail including building footprints, parks, and water features. This highest-fidelity option incurs longer initial load times (2-3 seconds) and occasional lag during rapid zoom changes, particularly in regions with complex street networks.

### Dynamic Information Display

Two context-sensitive information panels appear as overlays positioned within the map's right margin:

The **GEI Score Information Box** displays automatically upon successful address search, presenting four key metrics: GEI Overall Score, GEI Health Score, GEI Socioeconomic Score, and GEI Environmental Score. These values correspond to the census tract containing the user's search address, as determined by point-in-polygon spatial analysis. The box's blue color scheme and prominent positioning ensure visibility without obstructing the main map area.

The **CIMC Site Details Box** appears dynamically in response to user clicks on hazard site markers. Unlike the GEI box which shows persistent search location data, this panel displays transient information about the selected site: name, hazard category classification, distance from search address, numerical hazard score, and a clickable URL linking to EPA's detailed site report. A close button allows users to dismiss the panel, restoring full map visibility.

### Feature Breakdown Table

Below the map canvas, an expandable data table presents the top 10 contributing features for each of three GEI domains: Health, Socioeconomic, and Environment. Each feature row displays three values: a human-readable label describing the metric, the raw measured value for the census tract, and the percentile rank indicating how the tract compares to all U.S. tracts.

This transparency mechanism addresses a fundamental limitation of composite indices—scores are inherently abstract without visibility into constituent factors. The table enables users to understand why a particular tract received its score, identifying specific metrics driving the overall assessment. For instance, a tract with high GEI score might reveal elevated asthma rates, low insurance coverage, and proximity to industrial facilities as primary contributors.

---

## Innovative Design Elements

### Global Color Normalization Strategy

Traditional choropleth maps normalize color scales to the data range visible in the current viewport. While this maximizes local contrast, it creates misleading cross-region comparisons—a medium-scored tract in a high-risk region might display green (best in viewport) despite being worse than a red tract (worst in viewport) in a low-risk region.

This dashboard maintains a single global color scale calibrated to the full national dataset of all 73,000 census tracts. A tract with GEI score 0.7 displays the same color whether viewed in California or Kentucky, enabling users to assess absolute rather than relative risk. This design trades some local visual contrast for interpretive consistency across geographic contexts.

### Dual Independent Color Scales

The map simultaneously presents two choropleth representations—census tracts colored by GEI scores and CIMC sites colored by hazard scores—each with independent color scales and legends. This design requires careful attention to color theory: the census tract palette (blue gradient) and CIMC palette (yellow-orange-red) were specifically chosen for minimal perceptual interference. Avoiding overlapping hue ranges prevents user confusion about which color corresponds to which data layer.

The color bars position vertically aligned at different horizontal offsets to prevent overlap, though this manual positioning sacrifices responsive design—on narrow screens, legends may extend beyond viewport boundaries.

### Adaptive Performance Optimization

The basemap selector acknowledges that "one size fits all" visualization approaches often fail in practice. Users with slow internet connections or older hardware benefit from minimal basemap options, while those prioritizing cartographic detail accept longer load times for enhanced context. Providing explicit user control over performance-versus-fidelity tradeoffs represents a pragmatic acknowledgment of diverse deployment environments.

GeoPackage file format selection over GeoJSON provides another performance optimization. Although less universally supported, GeoPackage's binary encoding reduces file size by approximately 40% and eliminates client-side JSON parsing overhead—critical considerations when transmitting tens of thousands of polygon geometries.

### Geocoding Cache Implementation

Address geocoding via third-party APIs introduces latency and potential rate limiting. The dashboard implements an in-memory cache storing previously geocoded addresses, instantly returning coordinates for repeated searches without external API calls. This design particularly benefits iterative workflows where users repeatedly search the same location with different radius settings.

The cache persists only during the application session—cleared on server restart—avoiding potential staleness issues with long-term storage while still capturing most practical reuse scenarios.

### Data Processing Optimizations

The application employs several pandas optimization techniques to maintain responsive performance with large datasets. Rather than using the common but slow `iterrows()` method for iterating through DataFrames, the code utilizes `itertuples()` which is 10-100 times faster by returning lightweight namedtuples instead of full Series objects. This optimization significantly improves CIMC marker processing and feature table generation.

For distance filtering operations, the implementation uses vectorized operations and list comprehensions instead of row-by-row iteration. This approach processes coordinates in batch operations, reducing the overhead of repeated function calls and datatype conversions. These optimizations are particularly impactful when filtering CIMC sites within large search radii, improving calculation speed by 5-10x compared to naive iteration approaches.

Additional micro-optimizations include using dictionary unpacking for style object creation and attribute access instead of dictionary lookups where possible. While individually minor, these refinements collectively contribute to smoother user interactions, especially during rapid zoom changes or repeated searches.

---

## Implementation Challenges

### Hover Text Limitations

Plotly's default hover tooltip system provides basic templating capabilities but lacks sophisticated text formatting controls. Long CIMC site names frequently overflowed tooltip boundaries or wrapped unpredictably, creating truncated or illegible displays. The solution required implementing custom text wrapping logic that manually inserts line breaks at word boundaries to enforce maximum line lengths of 40 characters.

This preprocessing approach adds computational overhead during marker rendering, though optimizations using `itertuples()` for fast iteration help mitigate the performance impact. The implementation requires careful handling of special characters that might be misinterpreted as HTML entities. Ideally, the visualization library would provide CSS-like text wrapping controls within its native templating system, eliminating the need for custom preprocessing.

### Click Event Disambiguation

Plotly's click event system returns identical data structures regardless of which map element the user clicked—CIMC marker, census tract polygon, search indicator, or empty basemap space. Distinguishing between these click targets required implementing a "marker signature" system where only CIMC markers include specific metadata arrays. Click callbacks examine this metadata to determine whether a click represents genuine site selection or incidental map interaction.

This approach proved brittle during development, as inadvertently adding metadata to other trace types caused false-positive site selections. A more robust solution would involve trace-level identifiers explicitly indicating the clicked element's type.

### Color Bar Positioning Conflicts

When multiple traces include independent color scales, Plotly attempts automatic legend positioning but frequently produces overlapping results. Manual intervention via explicit pixel offsets proved necessary, with values determined through iterative trial-and-error. This hardcoded positioning breaks responsive design principles—the application assumes a minimum viewport width of approximately 1650 pixels to accommodate both map and legends.

Alternative approaches like horizontally stacked color bars or toggle-based single-scale display were considered but rejected due to either spatial inefficiency or reduced information density.

### Choropleth Rendering Performance

Despite optimizations, rendering thousands of census tract polygons remains computationally intensive. Initial page loads exhibit 2-3 second delays even with GeoPackage format and bounding box pre-filtering. Browser memory consumption spikes to 500MB during geometry parsing, occasionally triggering out-of-memory warnings on mobile devices.

The fundamental issue stems from Plotly's rendering architecture, which converts all geometries to SVG or Canvas elements client-side. Modern specialized mapping libraries use vector tile streaming and progressive level-of-detail rendering, displaying simplified geometries at low zoom and progressively adding detail during zoom-in operations. Plotly's static rendering approach lacks these optimizations.

The "No Basemap" mode partially mitigates this issue by eliminating tile server latency, though geometry rendering overhead persists. For datasets exceeding 10,000 polygons, alternative visualization libraries offering tile-based rendering may prove more performant.

### Spatial Information Panel Implementation

The GEI Score and CIMC Details information boxes appear as absolutely positioned HTML elements overlaying the map canvas. These panels are constructed using Dash's HTML component library (html.Div, html.H4, html.Strong, html.Span, html.Button, html.A), which provides Python-based HTML element generation. This approach arose from limitations in Plotly's native annotation system, which cannot accommodate interactive elements like close buttons or handle click-triggered visibility toggling.

Absolute positioning with hardcoded pixel offsets creates numerous design challenges: non-responsive layouts that break on mobile devices, z-index conflicts requiring manual stacking order management, and fragile positioning that breaks when map dimensions change. The boxes assume a fixed map size of 1400×1000 pixels—resizing the browser window or adjusting map dimensions causes misalignment.

Ideal implementations would use viewport-relative positioning or anchor points tied to geographic coordinates, but Plotly's architecture does not support such spatial anchoring for HTML overlay elements.

### Layer Toggle Limitations

Users cannot selectively show or hide individual map layers (census tracts, CIMC sites, search indicator) without modifying application code. Plotly maps lack native layer control widgets analogous to the legend-based toggling available in standard Plotly charts. The radius slider and basemap selector provide indirect control mechanisms, but comprehensive layer visibility management would require substantial custom widget development.

Specialized mapping libraries like Leaflet provide layer control out-of-box, but integrating such libraries into Dash requires mixing Python and JavaScript codebases—undermining Dash's primary appeal as a pure-Python framework.

---

## Comparative Assessment

### Strengths of the Plotly/Dash Approach

**Rapid Prototyping**: Building the dashboard required approximately 1,000 lines of Python code with no separate JavaScript, CSS, or HTML files. The entire user interface—from headings and paragraphs to tables and buttons—is constructed using Dash's HTML component library, which translates Python function calls into browser-rendered HTML. This unified Python-only workflow eliminates the need to manage multiple file types and languages. Comparable functionality in traditional web frameworks would require 3-4× the code volume across multiple languages.

**Declarative Visualization**: Plotly's graph object syntax enables clear, readable figure specifications where visual attributes directly correspond to code statements. Debugging and modification prove straightforward compared to imperative drawing APIs.

**Integrated Reactivity**: Dash's callback system automatically manages state updates and re-rendering, eliminating manual DOM manipulation and event listener management. This substantially reduces boilerplate code for interactive features.

**Python Ecosystem Integration**: Direct integration with pandas, numpy, and geopandas enables seamless data processing pipelines without serialization overhead between backend and frontend components.

### Alternative Technologies Considered

#### Initial Tableau Evaluation

The project initially considered Tableau as the visualization platform, given its reputation for rapid dashboard development and intuitive drag-and-drop interface. However, preliminary exploration quickly revealed critical limitations for our use case. Tableau's architecture fundamentally assumes static or semi-static data connections, making it poorly suited for dynamic, user-driven geocoding operations. The requirement for real-time address lookups via external APIs (Nominatim), on-the-fly distance calculations using the haversine formula, and dynamic spatial filtering of CIMC sites based on user-specified radii exceeded Tableau's computational model. Additionally, Tableau's limited Python integration and lack of support for custom geospatial libraries like GeoPandas made census tract point-in-polygon operations impractical. These constraints led to the decision to pursue a code-based solution offering full programmatic control over data processing and visualization logic.

#### Advanced Mapping Libraries Explored

Upon encountering various implementation challenges with Plotly/Dash, research identified several alternative mapping libraries that could potentially address these limitations:

**Mapbox GL JS**: A high-performance JavaScript mapping library utilizing GPU-accelerated rendering and vector tile streaming. Mapbox GL excels at visualizing large polygon datasets (like our 73,000 census tracts) through progressive level-of-detail rendering and supports advanced features including 3D terrain, building extrusions, and custom camera angles. Its powerful style specification language would have eliminated many of the manual positioning workarounds required in Plotly. However, implementing Mapbox GL would necessitate a multi-language codebase with separate backend API development for geocoding and spatial operations.

**Leaflet**: A lightweight (~40KB) JavaScript mapping library prioritizing simplicity and broad browser compatibility. Leaflet's extensive plugin ecosystem provides ready-made solutions for drawing tools, marker clustering, and layer controls—features that required extensive custom development in our Plotly implementation. The library's intuitive API and touch-friendly mobile interactions would address responsive design limitations encountered with absolute positioning. A Leaflet-based implementation could integrate with Dash via the Dash-Leaflet wrapper, maintaining some Python-centric workflow while accessing advanced mapping capabilities.

**D3.js**: A low-level JavaScript visualization library offering complete pixel-level control over every visual element. D3's geographic projection systems (d3-geo) and sophisticated data-join patterns would enable highly optimized custom rendering strategies, such as canvas-based drawing for census tracts instead of SVG elements. This approach could significantly improve performance but would require 2-3× more development time. D3 combined with Leaflet for basemap infrastructure represents a powerful architecture but necessitates JavaScript expertise and separate backend API development for Python-based geospatial processing.

**Folium**: A Python library that generates Leaflet.js maps, offering a bridge between Python data processing and advanced web mapping features. Folium maintains Python-based development while accessing Leaflet's performance optimizations and plugin ecosystem. However, Folium provides limited interactive callback support compared to Dash, making dynamic features like radius slider updates and click-triggered information panels more challenging to implement.

However, due to project time constraints and the learning curve associated with these JavaScript-based frameworks, we were unable to explore these options thoroughly. The decision to continue with Plotly/Dash was pragmatic—leveraging existing team expertise to deliver a functional prototype within the available timeline. Implementing any JavaScript-based alternative would have required separating backend (Flask/FastAPI for geocoding, distance calculations, and spatial queries) from frontend visualization, essentially doubling the architectural complexity. Future iterations of this dashboard could benefit from evaluating these alternatives, particularly for production deployments requiring mobile responsiveness, advanced cartographic controls, or improved performance with large geographic datasets.

---

## Conclusion

The Geo-Equity Index Dashboard leverages Plotly and Dash to communicate multi-dimensional environmental health risk data through layered choropleth representations, dynamic filtering mechanisms, and context-aware information displays. The pure-Python implementation enabled rapid prototyping in a single unified codebase—an approach that would have required significantly more code distributed across multiple languages (JavaScript, HTML, CSS, Python) with traditional web frameworks.

Nevertheless, the implementation revealed limitations inherent to adapting general-purpose visualization libraries for specialized geospatial applications. Specific challenges emerged in three areas: hover text formatting, click event disambiguation, and spatial information panel positioning. These required custom workarounds that exposed gaps in Plotly's abstraction layer for mapping-specific requirements. Additionally, performance constraints with large polygon datasets (>10,000 features) highlighted computational tradeoffs compared to specialized mapping libraries employing vector tile architectures and progressive rendering strategies. Research into alternatives including Mapbox GL JS, Leaflet, and D3.js revealed these JavaScript-based libraries offer superior performance and cartographic features, but at the cost of increased architectural complexity and multi-language development requirements.

The findings suggest that technology selection should align with application context and deployment requirements. For this project, where development velocity and Python ecosystem integration are prioritized, the Plotly/Dash framework provides an effective solution that minimizes time-to-functionality. However, production applications requiring mobile responsiveness, advanced cartographic interactions, or handling large-scale geographic datasets may benefit from specialized mapping libraries. Optimal architectures for such deployments might combine Python-based backend processing (GeoPandas, Shapely) with JavaScript-based rendering frontends (Leaflet, Mapbox GL), or explore hybrid solutions like Dash-Leaflet that bridge both ecosystems while accepting some tradeoffs in either development simplicity or feature completeness.

---

## Future Enhancements

### Interactive Map Exploration

A key enhancement under consideration involves enabling direct map interaction for location selection, moving beyond the current text-based address search to support more intuitive visual exploration.

**Proposed Capabilities:**

**Viewport-Based Exploration**: Users could pan and zoom freely across the map to explore different regions, with census tract data and CIMC sites loading dynamically based on the visible area. This would enable comparative regional analysis without requiring knowledge of specific addresses.

**Pin Dropping**: Users could click anywhere on the map to drop a pin, instantly retrieving GEI scores and nearby hazardous sites for that exact location. This familiar interaction pattern would make the tool more accessible to users accustomed to consumer mapping applications.

**Key Implementation Considerations:**

- Reverse geocoding capability to convert map coordinates back to readable addresses
- Map event detection to distinguish between pin-dropping clicks and other interactions
- Dynamic data loading strategies to efficiently handle viewport changes
- Draggable pins that update information in real-time as they are moved
- Performance optimizations to maintain responsiveness with large datasets during zoom operations

This enhancement would transform the dashboard from an address-centric tool into a map-centric exploration platform, enabling users to discover health equity patterns through visual browsing rather than targeted searches. Given the architectural complexity and performance considerations involved, this feature represents a logical next phase following validation of the current prototype with users.

---

**Document Information:**
- **Date:** November 15, 2025
- **Project:** CSE 6242 Final Project - Team 86
- **Focus:** Visualization Review
