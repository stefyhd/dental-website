/* =========================================================
   Interacțiunile site-ului public.
   ========================================================= */

(function () {
    "use strict";

    /* Molar văzut din lateral: coroană lată cu două cuspide, gât strâns,
       două rădăcini care se depărtează. Silueta veche era o picătură. */
    var TOOTH = "M 38 62 C 40 38, 56 24, 74 26 C 86 27, 90 40, 100 40 " +
                "C 110 40, 114 27, 126 26 C 144 24, 160 38, 162 62 " +
                "C 165 84, 160 106, 150 120 C 145 127, 144 140, 144 156 " +
                "C 144 184, 139 210, 133 226 C 129 237, 116 237, 114 226 " +
                "C 110 200, 107 174, 104 152 C 102 142, 98 142, 96 152 " +
                "C 93 174, 90 200, 86 226 C 84 237, 71 237, 67 226 " +
                "C 61 210, 56 184, 56 156 C 56 140, 55 127, 50 120 " +
                "C 40 106, 35 84, 38 62 Z";

    var LAYERS = 26;   /* mai multe = mai solid, dar mai scump de desenat */
    var STEP = 1.6;    /* px între straturi pe axa Z */

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
        var front = [255, 255, 255];
        var back = [124, 150, 138];   /* verde-gri rece: intră în fundal */

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