/*
 * Desert Trash GJ - Interactive Map
 *
 * Initializes a Mapbox GL JS map centered on Mesa County, loads
 * dumping-report submissions as clustered GeoJSON markers, and
 * provides a filter sidebar for category/severity/status/date.
 *
 * Globals expected (set by Django template):
 *   window.MAPBOX_TOKEN  - Mapbox access token
 *   window.GEOJSON_URL   - URL for the GeoJSON endpoint
 */

(function () {
    "use strict";

    /* ------------------------------------------------------------------ */
    /*  Map initialization                                                 */
    /* ------------------------------------------------------------------ */

    mapboxgl.accessToken = window.MAPBOX_TOKEN;

    var map = new mapboxgl.Map({
        container: "map",
        style: "mapbox://styles/mapbox/outdoors-v12",
        center: [-108.55, 39.07],   // Mesa County, CO
        zoom: 10
    });

    // Navigation controls (zoom +/-, compass)
    map.addControl(new mapboxgl.NavigationControl(), "top-right");

    /* ------------------------------------------------------------------ */
    /*  Build GeoJSON URL with current filter values                       */
    /* ------------------------------------------------------------------ */

    function buildGeoJSONUrl() {
        var params = [];

        // Category checkboxes - collect checked slugs
        var checked = document.querySelectorAll(".category-checkbox:checked");
        for (var i = 0; i < checked.length; i++) {
            params.push("category=" + encodeURIComponent(checked[i].value));
        }

        // Severity select
        var severity = document.getElementById("filter-severity");
        if (severity && severity.value) {
            params.push("severity=" + encodeURIComponent(severity.value));
        }

        // Status select
        var status = document.getElementById("filter-status");
        if (status && status.value) {
            params.push("status=" + encodeURIComponent(status.value));
        }

        // Date range
        var dateFrom = document.getElementById("filter-date-from");
        if (dateFrom && dateFrom.value) {
            params.push("date_from=" + encodeURIComponent(dateFrom.value));
        }
        var dateTo = document.getElementById("filter-date-to");
        if (dateTo && dateTo.value) {
            params.push("date_to=" + encodeURIComponent(dateTo.value));
        }

        var url = window.GEOJSON_URL;
        if (params.length > 0) {
            url += "?" + params.join("&");
        }
        return url;
    }

    /* ------------------------------------------------------------------ */
    /*  Load / reload GeoJSON data                                         */
    /* ------------------------------------------------------------------ */

    function loadSubmissions() {
        var url = buildGeoJSONUrl();

        fetch(url)
            .then(function (response) { return response.json(); })
            .then(function (data) {
                var source = map.getSource("submissions");
                if (source) {
                    // Update existing source
                    source.setData(data);
                } else {
                    // First load - add source and layers
                    addSourceAndLayers(data);
                }
            })
            .catch(function (err) {
                console.error("Failed to load submissions:", err);
            });
    }

    /* ------------------------------------------------------------------ */
    /*  Map source + layers (clusters, cluster counts, markers)            */
    /* ------------------------------------------------------------------ */

    function addSourceAndLayers(data) {
        // Clustered GeoJSON source
        map.addSource("submissions", {
            type: "geojson",
            data: data,
            cluster: true,
            clusterMaxZoom: 14,
            clusterRadius: 50
        });

        // Cluster circle layer
        map.addLayer({
            id: "clusters",
            type: "circle",
            source: "submissions",
            filter: ["has", "point_count"],
            paint: {
                "circle-color": [
                    "step", ["get", "point_count"],
                    "#51bbd6",   // < 10: blue
                    10, "#f1f075", // 10-49: yellow
                    50, "#f28cb1"  // 50+: pink
                ],
                "circle-radius": [
                    "step", ["get", "point_count"],
                    18,         // < 10
                    10, 24,     // 10-49
                    50, 32      // 50+
                ],
                "circle-stroke-width": 2,
                "circle-stroke-color": "#fff"
            }
        });

        // Cluster count labels
        map.addLayer({
            id: "cluster-count",
            type: "symbol",
            source: "submissions",
            filter: ["has", "point_count"],
            layout: {
                "text-field": ["get", "point_count_abbreviated"],
                "text-font": ["DIN Pro Medium", "Arial Unicode MS Bold"],
                "text-size": 13
            },
            paint: {
                "text-color": "#fff"
            }
        });

        // Individual markers - colored by category
        map.addLayer({
            id: "unclustered-point",
            type: "circle",
            source: "submissions",
            filter: ["!", ["has", "point_count"]],
            paint: {
                "circle-color": ["get", "color"],
                "circle-radius": 8,
                "circle-stroke-width": 2,
                "circle-stroke-color": "#fff"
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /*  Click handlers: cluster zoom + marker popups                       */
    /* ------------------------------------------------------------------ */

    map.on("load", function () {
        // Load initial data
        loadSubmissions();

        // Click cluster to zoom in
        map.on("click", "clusters", function (e) {
            var features = map.queryRenderedFeatures(e.point, { layers: ["clusters"] });
            var clusterId = features[0].properties.cluster_id;
            map.getSource("submissions").getClusterExpansionZoom(clusterId, function (err, zoom) {
                if (err) return;
                map.easeTo({
                    center: features[0].geometry.coordinates,
                    zoom: zoom
                });
            });
        });

        // Click individual marker to show popup
        map.on("click", "unclustered-point", function (e) {
            var feature = e.features[0];
            var coords = feature.geometry.coordinates.slice();
            var props = feature.properties;

            // Build popup HTML
            var html = '';
            if (props.photo_url) {
                html += '<img class="popup-thumb" src="' + escapeHtml(props.photo_url) + '" alt="">';
            }
            html += '<div class="popup-title"><a href="' + escapeHtml(props.detail_url) + '">' + escapeHtml(props.category_name) + '</a></div>';
            html += '<div class="popup-category">';
            html += '<span class="category-swatch" style="background:' + escapeHtml(props.color) + '"></span>';
            html += '<span class="popup-severity ' + escapeHtml(props.severity) + '">' + escapeHtml(props.severity) + '</span>';
            html += '</div>';
            if (props.description) {
                html += '<div>' + escapeHtml(props.description) + '</div>';
            }
            html += '<div class="popup-meta">';
            html += escapeHtml(props.status_display) + ' &middot; ' + escapeHtml(props.created_at);
            html += '</div>';

            // Ensure popup shows at correct location if map wraps
            while (Math.abs(e.lngLat.lng - coords[0]) > 180) {
                coords[0] += e.lngLat.lng > coords[0] ? 360 : -360;
            }

            new mapboxgl.Popup({ offset: 12 })
                .setLngLat(coords)
                .setHTML(html)
                .addTo(map);
        });

        // Pointer cursor on interactive layers
        map.on("mouseenter", "clusters", function () {
            map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "clusters", function () {
            map.getCanvas().style.cursor = "";
        });
        map.on("mouseenter", "unclustered-point", function () {
            map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "unclustered-point", function () {
            map.getCanvas().style.cursor = "";
        });
    });

    /* ------------------------------------------------------------------ */
    /*  Filter sidebar controls                                            */
    /* ------------------------------------------------------------------ */

    var applyBtn = document.getElementById("filter-apply");
    var resetBtn = document.getElementById("filter-reset");

    if (applyBtn) {
        applyBtn.addEventListener("click", function () {
            loadSubmissions();
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener("click", function () {
            // Reset all filter controls
            var checkboxes = document.querySelectorAll(".category-checkbox");
            for (var i = 0; i < checkboxes.length; i++) {
                checkboxes[i].checked = true;
            }
            var severity = document.getElementById("filter-severity");
            if (severity) severity.value = "";
            var status = document.getElementById("filter-status");
            if (status) status.value = "";
            var dateFrom = document.getElementById("filter-date-from");
            if (dateFrom) dateFrom.value = "";
            var dateTo = document.getElementById("filter-date-to");
            if (dateTo) dateTo.value = "";

            // Re-fetch with cleared filters
            loadSubmissions();
        });
    }

    /* ------------------------------------------------------------------ */
    /*  Mobile sidebar toggle                                              */
    /* ------------------------------------------------------------------ */

    var sidebarToggle = document.getElementById("sidebar-toggle");
    var sidebar = document.getElementById("sidebar");

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("visible");
            sidebarToggle.textContent = sidebar.classList.contains("visible") ? "\u2715" : "\u2630";
        });
    }

    /* ------------------------------------------------------------------ */
    /*  Utility: escape HTML to prevent XSS in popups                      */
    /* ------------------------------------------------------------------ */

    function escapeHtml(str) {
        if (!str) return "";
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

})();
