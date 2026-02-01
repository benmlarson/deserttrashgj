/*
 * Desert Trash GJ - Moderation Detail Map
 *
 * Renders a static Mapbox map centered on the submission location.
 *
 * Globals expected (set by Django template):
 *   window.SUBMISSION_LAT  - Latitude of the submission
 *   window.SUBMISSION_LNG  - Longitude of the submission
 *   window.MAPBOX_TOKEN    - Mapbox access token
 */

(function () {
    "use strict";

    var lat = window.SUBMISSION_LAT;
    var lng = window.SUBMISSION_LNG;
    var token = window.MAPBOX_TOKEN;

    if (!lat || !lng || !token) return;

    var mapContainer = document.getElementById("detail-map");
    if (!mapContainer) return;

    mapboxgl.accessToken = token;

    var map = new mapboxgl.Map({
        container: "detail-map",
        style: "mapbox://styles/mapbox/outdoors-v12",
        center: [lng, lat],
        zoom: 15,
        interactive: false
    });

    new mapboxgl.Marker()
        .setLngLat([lng, lat])
        .addTo(map);
})();
