/*
 * Desert Trash GJ - Submit Form
 *
 * Handles photo preview, client-side EXIF GPS extraction,
 * Mapbox pin placement, and form validation.
 *
 * Globals expected (set by Django template):
 *   window.MAPBOX_TOKEN - Mapbox access token
 */

(function () {
    "use strict";

    var latInput = document.getElementById("id_latitude");
    var lngInput = document.getElementById("id_longitude");
    var coordsDisplay = document.getElementById("coords-display");
    var exifStatus = document.getElementById("exif-status");
    var photoInput = document.getElementById("id_photo");
    var previewArea = document.getElementById("photo-preview-area");
    var submitBtn = document.getElementById("submit-btn");

    /* ------------------------------------------------------------------ */
    /*  Mapbox pin map                                                     */
    /* ------------------------------------------------------------------ */

    mapboxgl.accessToken = window.MAPBOX_TOKEN;

    var map = new mapboxgl.Map({
        container: "pin-map",
        style: "mapbox://styles/mapbox/outdoors-v12",
        center: [-108.55, 39.07],
        zoom: 10,
    });

    map.addControl(new mapboxgl.NavigationControl(), "top-right");
    map.addControl(
        new mapboxgl.GeolocateControl({
            positionOptions: { enableHighAccuracy: true },
            trackUserLocation: false,
        }),
        "top-right"
    );

    var marker = null;

    function placeMarker(lng, lat) {
        if (marker) {
            marker.setLngLat([lng, lat]);
        } else {
            marker = new mapboxgl.Marker({ draggable: true })
                .setLngLat([lng, lat])
                .addTo(map);

            marker.on("dragend", function () {
                var pos = marker.getLngLat();
                updateCoords(pos.lng, pos.lat);
            });
        }
        updateCoords(lng, lat);
    }

    function updateCoords(lng, lat) {
        latInput.value = lat.toFixed(6);
        lngInput.value = lng.toFixed(6);
        coordsDisplay.textContent = lat.toFixed(6) + ", " + lng.toFixed(6);
    }

    map.on("click", function (e) {
        placeMarker(e.lngLat.lng, e.lngLat.lat);
    });

    /* ------------------------------------------------------------------ */
    /*  Photo preview                                                      */
    /* ------------------------------------------------------------------ */

    if (photoInput) {
        photoInput.addEventListener("change", function () {
            previewArea.innerHTML = "";
            exifStatus.textContent = "";

            var file = this.files && this.files[0];
            if (!file) return;

            // Show preview
            var reader = new FileReader();
            reader.onload = function (e) {
                var img = document.createElement("img");
                img.src = e.target.result;
                previewArea.appendChild(img);
            };
            reader.readAsDataURL(file);

            // Try client-side EXIF GPS extraction
            extractExifGps(file);
        });
    }

    /* ------------------------------------------------------------------ */
    /*  Client-side EXIF GPS extraction                                    */
    /* ------------------------------------------------------------------ */

    function extractExifGps(file) {
        // Read first 128KB for EXIF data
        var slice = file.slice(0, 131072);
        var reader = new FileReader();
        reader.onload = function (e) {
            var coords = parseExifGps(new DataView(e.target.result));
            if (coords) {
                exifStatus.textContent = "Location detected from photo";
                placeMarker(coords[1], coords[0]);
                map.flyTo({ center: [coords[1], coords[0]], zoom: 14 });
            }
        };
        reader.readAsArrayBuffer(slice);
    }

    function parseExifGps(view) {
        // Find JPEG SOI
        if (view.byteLength < 4 || view.getUint16(0) !== 0xffd8) return null;

        var offset = 2;
        while (offset < view.byteLength - 4) {
            var marker = view.getUint16(offset);
            if (marker === 0xffe1) {
                // APP1 marker - EXIF data
                var length = view.getUint16(offset + 2);
                return parseApp1(view, offset + 4, length - 2);
            }
            // Skip to next marker
            var segLen = view.getUint16(offset + 2);
            offset += 2 + segLen;
        }
        return null;
    }

    function parseApp1(view, start, length) {
        // Check for "Exif\0\0"
        if (start + 6 > view.byteLength) return null;
        if (
            view.getUint8(start) !== 0x45 ||     // E
            view.getUint8(start + 1) !== 0x78 || // x
            view.getUint8(start + 2) !== 0x69 || // i
            view.getUint8(start + 3) !== 0x66    // f
        ) return null;

        var tiffStart = start + 6;
        if (tiffStart + 8 > view.byteLength) return null;

        // Determine byte order
        var byteOrder = view.getUint16(tiffStart);
        var littleEndian = byteOrder === 0x4949; // "II"

        // Read IFD0 offset
        var ifd0Offset = view.getUint32(tiffStart + 4, littleEndian);
        return readIfdForGps(view, tiffStart, tiffStart + ifd0Offset, littleEndian);
    }

    function readIfdForGps(view, tiffStart, ifdOffset, le) {
        if (ifdOffset + 2 > view.byteLength) return null;
        var entries = view.getUint16(ifdOffset, le);
        var gpsIfdOffset = null;

        for (var i = 0; i < entries; i++) {
            var entryOffset = ifdOffset + 2 + i * 12;
            if (entryOffset + 12 > view.byteLength) return null;
            var tag = view.getUint16(entryOffset, le);
            if (tag === 0x8825) {
                // GPSInfo tag - value is offset to GPS IFD
                gpsIfdOffset = view.getUint32(entryOffset + 8, le);
                break;
            }
        }

        if (gpsIfdOffset === null) return null;
        return readGpsIfd(view, tiffStart, tiffStart + gpsIfdOffset, le);
    }

    function readGpsIfd(view, tiffStart, ifdOffset, le) {
        if (ifdOffset + 2 > view.byteLength) return null;
        var entries = view.getUint16(ifdOffset, le);
        var gpsData = {};

        for (var i = 0; i < entries; i++) {
            var entryOffset = ifdOffset + 2 + i * 12;
            if (entryOffset + 12 > view.byteLength) return null;
            var tag = view.getUint16(entryOffset, le);
            var type = view.getUint16(entryOffset + 2, le);
            var count = view.getUint32(entryOffset + 4, le);

            if (tag === 1 || tag === 3) {
                // GPSLatitudeRef (1) or GPSLongitudeRef (3) - ASCII
                gpsData[tag] = String.fromCharCode(view.getUint8(entryOffset + 8));
            } else if (tag === 2 || tag === 4) {
                // GPSLatitude (2) or GPSLongitude (4) - 3 RATIONAL values
                if (type === 5 && count === 3) {
                    var valOffset = tiffStart + view.getUint32(entryOffset + 8, le);
                    if (valOffset + 24 > view.byteLength) return null;
                    var d = view.getUint32(valOffset, le) / view.getUint32(valOffset + 4, le);
                    var m = view.getUint32(valOffset + 8, le) / view.getUint32(valOffset + 12, le);
                    var s = view.getUint32(valOffset + 16, le) / view.getUint32(valOffset + 20, le);
                    gpsData[tag] = d + m / 60 + s / 3600;
                }
            }
        }

        if (gpsData[1] && gpsData[2] && gpsData[3] && gpsData[4]) {
            var lat = gpsData[2];
            var lng = gpsData[4];
            if (gpsData[1] === "S") lat = -lat;
            if (gpsData[3] === "W") lng = -lng;
            return [lat, lng];
        }
        return null;
    }

    /* ------------------------------------------------------------------ */
    /*  Client-side validation                                             */
    /* ------------------------------------------------------------------ */

    var form = document.getElementById("submit-form");
    var hasTempPhoto = !!document.querySelector('input[name="temp_photo"]');

    if (form) {
        form.addEventListener("submit", function (e) {
            var hasNewFile = photoInput.files && photoInput.files.length > 0;
            if (!hasNewFile && !hasTempPhoto) {
                e.preventDefault();
                alert("Please select a photo.");
                return;
            }
            if (hasNewFile) {
                var file = photoInput.files[0];
                if (file.size > 20 * 1024 * 1024) {
                    e.preventDefault();
                    alert("Photo must be under 20 MB.");
                    return;
                }
            }
            // Disable button to prevent double-submit
            submitBtn.disabled = true;
            submitBtn.textContent = "Submitting\u2026";
        });
    }

})();
