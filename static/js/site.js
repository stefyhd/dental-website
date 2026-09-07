/* =========================================================
   Interacțiunile site-ului public.
   ========================================================= */

(function () {
    "use strict";

    var TOOTH = "M100 20 C55 20, 32 50, 36 92 C40 130, 52 178, 66 218 " +
                "C72 236, 92 238, 95 218 L100 168 L105 218 " +
                "C108 238, 128 236, 134 218 C148 178, 160 130, 164 92 " +
                "C168 50, 145 20, 100 20 Z";

    var LAYERS = 26;   /* mai multe = mai solid, dar mai scump de desenat */
    var STEP = 1.4;    /* px între straturi pe axa Z */

    /* -----------------------------------------------------
       Dintele 3D.

       Nu încărcăm o bibliotecă 3D și nu avem model. Extrudăm
       silueta: 26 de copii ale conturului, așezate una în
       spatele alteia pe Z, de la clar în față la umbrit în
       spate. Rotit, parallaxul dintre straturi citește ca un
       volum real — și cântărește cât un SVG.
       ----------------------------------------------------- */
    function mix(a, b, t) {
        return a.map(function (v, i) { return Math.round(v + (b[i] - v) * t); });
    }

    function buildTooth(stage) {
        var front = [253, 251, 246];
        var back = [150, 165, 146];

        var solid = document.createElement("div");
        solid.className = "tooth-3d";

        for (var i = 0; i < LAYERS; i++) {
            var t = i / (LAYERS - 1);
            var rgb = mix(front, back, t);

            var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute("viewBox", "0 0 200 250");
            svg.setAttribute("aria-hidden", "true");
            svg.style.transform = "translateZ(" + (-i * STEP) + "px)";

            var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", TOOTH);
            path.setAttribute("fill", "rgb(" + rgb.join(",") + ")");

            svg.appendChild(path);
            solid.appendChild(svg);
        }

        stage.innerHTML = "";
        stage.appendChild(solid);
    }

    var stage = document.querySelector("[data-tooth]");
    var calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var wide = window.matchMedia("(min-width: 769px)").matches;

    /* Pe telefon forma e ascunsă oricum, deci n-are rost s-o construim. */
    if (stage && wide && !calm) {
        buildTooth(stage);
    }


    /* -----------------------------------------------------
       Înainte / după. Un input range invizibil face toată
       treaba: merge cu mouse, cu deget și cu tastatura, fără
       să scriem noi logica de accesibilitate.
       ----------------------------------------------------- */
    document.querySelectorAll(".ba").forEach(function (box) {
        var range = box.querySelector(".ba-range");
        if (!range) return;

        var apply = function () {
            box.style.setProperty("--pos", range.value + "%");
        };

        range.addEventListener("input", apply);
        apply();
    });


    /* -----------------------------------------------------
       Harta se încarcă la cerere. Până apeși, nicio cerere
       către Google și niciun cookie.
       ----------------------------------------------------- */
    document.querySelectorAll(".map").forEach(function (frame) {
        var button = frame.querySelector(".map-ask");
        if (!button) return;

        button.addEventListener("click", function () {
            var iframe = document.createElement("iframe");
            iframe.src = frame.dataset.map;
            iframe.loading = "lazy";
            iframe.title = "Harta cabinetului";
            iframe.referrerPolicy = "no-referrer-when-downgrade";
            iframe.allowFullscreen = true;

            button.remove();
            frame.appendChild(iframe);
        });
    });
})();