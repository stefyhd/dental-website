/* =========================================================
   Interacțiunile site-ului public.
   ========================================================= */

(function () {
    "use strict";

    var calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var wide = window.matchMedia("(min-width: 769px)").matches;

    /* -----------------------------------------------------
       Dintele 3D.

       Modelul e un molar real (glTF binar, 220 KB) afișat cu
       <model-viewer> de la Google. Nu scriem Three.js: eticheta
       se ocupă singură de cameră, lumini și rotire.

       Îl încărcăm DOAR pe desktop și doar prin JS, ca telefonul
       să nu ia nici modelul, nici biblioteca. Până se încarcă
       (și dacă nu se încarcă deloc) rămâne silueta plată din
       HTML, deci hero-ul nu are niciodată o gaură.
       ----------------------------------------------------- */
    function loadTooth(stage) {
        var src = stage.dataset.model;
        if (!src || !stage.dataset.lib) return;

        /* Biblioteca stă în static/, nu pe un CDN. Un CDN ar trimite
           IP-ul vizitatorului către alt server înainte de orice acord —
           exact ce evităm și la hartă. */
        var lib = document.createElement("script");
        lib.type = "module";
        lib.src = stage.dataset.lib;
        document.head.appendChild(lib);

        var mv = document.createElement("model-viewer");
        mv.className = "tooth-3d";
        mv.setAttribute("src", src);
        mv.setAttribute("alt", "Model 3D al unui molar");
        mv.setAttribute("camera-orbit", "0deg 80deg 116%");
        mv.setAttribute("field-of-view", "24deg");
        mv.setAttribute("environment-image", "neutral");
        mv.setAttribute("exposure", "1.45");
        mv.setAttribute("shadow-intensity", "0");
        mv.setAttribute("disable-zoom", "");
        mv.setAttribute("disable-tap", "");
        mv.setAttribute("interaction-prompt", "none");
        mv.addEventListener("load", function () {
            /* Modelul vine gri de pe Sketchfab. Îl facem alb de smalț.
               ATENȚIE la `roughness`: la 0.35 dintele iese mat, ca de
               ipsos. Smalțul are luciu — 0.16 (aproape cât originalul,
               0.165) readuce reflexiile de pe cuspide. */
            var material = mv.model && mv.model.materials[0];
            if (material) {
                material.pbrMetallicRoughness.setBaseColorFactor([1, 1, 1, 1]);
                material.pbrMetallicRoughness.setMetallicFactor(0.06);
                material.pbrMetallicRoughness.setRoughnessFactor(0.16);
            }
            stage.classList.add("ready");
        });

        if (!calm) {
            mv.setAttribute("auto-rotate", "");
            mv.setAttribute("auto-rotate-delay", "300");
            mv.setAttribute("rotation-per-second", "16deg");
        }

        mv.addEventListener("load", function () {
            /* Modelul vine gri de pe Sketchfab. Îl facem alb de smalț. */
            var material = mv.model && mv.model.materials[0];
            if (material) {
                material.pbrMetallicRoughness.setBaseColorFactor([1, 1, 1, 1]);
                material.pbrMetallicRoughness.setMetallicFactor(0);
                material.pbrMetallicRoughness.setRoughnessFactor(0.35);
            }
            stage.classList.add("ready");
        });

        stage.appendChild(mv);
    }

    var stage = document.querySelector("[data-tooth]");

    if (stage && wide) {
        loadTooth(stage);
    }

    /* -----------------------------------------------------
       Etichetele „+".

       Nu sunt fixe: apar și dispar continuu, pe poziții alese
       aleator dintr-un set de sloturi care ocolesc dintele.
       Trei odată, ca să nu se aglomereze forma.

       Ca să adaugi/scoți un beneficiu, editează DOAR lista de
       mai jos.
    ----------------------------------------------------- */
    var PLUS_TEXT = [
        "Anestezie fără durere",
        "Radiografie pe loc",
        "Preț spus înainte",
        "Plan de tratament scris",
        "Sterilizare documentată",
        "Garanție scrisă la lucrări",
        "Urgențe în aceeași zi",
        "Același medic de fiecare dată"
    ];

    /* Sloturile ocolesc mijlocul, unde stă dintele. */
    var PLUS_SLOTS = [
        { top: "18%", side: "right" },
        { top: "33%", side: "right" },
        { top: "49%", side: "left" },
        { top: "65%", side: "left" },
        { top: "78%", side: "left" },
        { top: "25%", side: "right" },
        { top: "42%", side: "right" },
        { top: "58%", side: "right" },

    ];

    var PLUS_SHOWN = 3;      /* câte se văd în același timp */
    var PLUS_FADE = 500;     /* ms, trebuie să fie cât tranziția din CSS */ 
    var PLUS_GAP = 15;        /* câte de pixeli de la altă etichetă pentru a fi liber */

  

    function pick(list) {
        return list[Math.floor(Math.random() * list.length)];
    }

        function startPlusField(field) {
        var live = [];

        function height(slot) { return parseFloat(slot.top); }

        function spawn() {
            /* Un slot e liber dacă nu e ocupat ȘI dacă nu e prea aproape
               pe verticală de altă etichetă. Fără regula a doua, una din
               stânga și una din centru pot ajunge la aceeași înălțime și
               se suprapun. */
            var slots = PLUS_SLOTS.filter(function (slot) {
                return live.every(function (item) {
                    return item.slot !== slot &&
                           Math.abs(height(item.slot) - height(slot)) >= PLUS_GAP;
                });
            });
            var texts = PLUS_TEXT.filter(function (text) {
                return live.every(function (item) { return item.text !== text; });
            });
            if (!slots.length || !texts.length) return;

            var slot = pick(slots);
            var text = pick(texts);

            var el = document.createElement("span");
            el.className = "plus plus-" + slot.side;
            el.style.top = slot.top;
            el.innerHTML = "<i>+</i>";
            el.appendChild(document.createTextNode(text));

            field.appendChild(el);

            /* Citirea asta forțează browserul să calculeze layoutul acum,
               ca tranziția să pornească de la opacity 0 în loc să sară
               direct la 1. Fără ea, elementul apare instantaneu. */
            void el.offsetWidth;
            el.classList.add("on");

            var item = { slot: slot, text: text };
            live.push(item);

            setTimeout(function () {
                el.classList.remove("on");
                setTimeout(function () {
                    el.remove();
                    live.splice(live.indexOf(item), 1);
                }, PLUS_FADE);
            }, 4500 + Math.random() * 3000);
        }

        /* Scoatem cele trei etichete statice din HTML — de aici încolo
           le construiește JS-ul. */
        field.innerHTML = "";

        for (var i = 0; i < PLUS_SHOWN; i++) {
            setTimeout(spawn, i * 700);
        }
        setInterval(function () {
            if (live.length < PLUS_SHOWN) spawn();
        }, 1400);
    }

    var field = document.querySelector("[data-plus]");

    /* Cu „reduce motion" pornit rămân cele trei din HTML, nemișcate. */
    if (field && !calm) {
        startPlusField(field);
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


    