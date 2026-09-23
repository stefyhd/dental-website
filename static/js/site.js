/* =========================================================
   Interacțiunile site-ului public.

   Patru lucruri, în ordine:
     1. dintele 3D din hero
     2. etichetele „+" care apar și dispar peste el
     3. comparatorul înainte/după
     4. harta, încărcată abia la click
   ========================================================= */

(function () {
    "use strict";

    var calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function pick(list) {
        return list[Math.floor(Math.random() * list.length)];
    }

    /* Modelul plus biblioteca fac ~400 KB. Merită pe orice ecran — pe
       telefon silueta plată arată vizibil mai prost — dar nu pe o
       conexiune proastă sau cu „economie de date" pornită. */
    function connectionIsFine() {
        var net = navigator.connection;
        if (!net) return true;
        if (net.saveData) return false;
        return ["slow-2g", "2g", "3g"].indexOf(net.effectiveType) < 0;
    }


    /* =====================================================
       1. DINTELE 3D

       Modelul e molarul din Sketchfab, convertit în glTF
       binar (220 KB) și afișat cu <model-viewer> de la
       Google. Nu scriem Three.js: eticheta se ocupă singură
       de cameră, lumini și rotire.

       Se încarcă pe orice ecran, dar abia după ce pagina s-a
       desenat, și deloc pe conexiuni proaste. Până vine — și
       dacă nu vine deloc — rămâne silueta plată din HTML, deci
       hero-ul nu are niciodată o gaură.

       REGLAJE:
         TOOTH_ZOOM      cât de mare e dintele (mai mic = mai mare)
         TOOTH_TILT      unghiul pe verticală (90 = fix din față)
         TOOTH_SPIN      viteza rotirii
         TOOTH_GLOSS     luciul smalțului (0 = oglindă, 1 = mat)
         TOOTH_LIGHT     luminozitatea
       ===================================================== */

    var TOOTH_ZOOM  = "93%";
    var TOOTH_TILT  = "70deg";
    var TOOTH_SPIN  = "13deg";
    var TOOTH_GLOSS = 0.12;
    var TOOTH_LIGHT = "1.0";

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
        /* Fără `field-of-view` explicit: model-viewer încadrează singur
           modelul în caseta lui, iar `TOOTH_ZOOM` e procent din acea
           încadrare. 100% = exact cât încape, 120% = mai mic.
           Cu field-of-view fix, procentul nu mai încadra nimic și
           dintele ieșea din casetă oricât îl reglai. */
        mv.setAttribute("camera-orbit", "0deg " + TOOTH_TILT + " " + TOOTH_ZOOM);
        mv.setAttribute("environment-image", "legacy");
        mv.setAttribute("tone-mapping", "aces");
        mv.setAttribute("exposure", TOOTH_LIGHT);
        mv.setAttribute("shadow-intensity", "0");
        mv.setAttribute("disable-zoom", "");
        mv.setAttribute("disable-tap", "");
        mv.setAttribute("interaction-prompt", "none");

        if (!calm) {
            mv.setAttribute("auto-rotate", "");
            mv.setAttribute("auto-rotate-delay", "300");
            mv.setAttribute("rotation-per-second", TOOTH_SPIN);
        }

       mv.addEventListener("load", function () {
            var materials = mv.model ? mv.model.materials : [];

            materials.forEach(function (material) {
                var pbr = material.pbrMetallicRoughness;

                pbr.setBaseColorFactor([0.92, 0.92, 0.92, 1]);
                pbr.setMetallicFactor(0.02);
                pbr.setRoughnessFactor(TOOTH_GLOSS);

                material.setClearcoatFactor(0.75);
                material.setClearcoatRoughnessFactor(0.08);
            });

            stage.classList.add("ready");
        });

        stage.appendChild(mv);
    }

    var toothStage = document.querySelector("[data-tooth]");

    /* Amânat până după `load`: modelul e decor, n-are voie să întârzie
       nici textul, nici butoanele. Până vine, se vede silueta plată. */
    if (toothStage && connectionIsFine()) {
        window.addEventListener("load", function () {
            var start = function () { loadTooth(toothStage); };
            if (window.requestIdleCallback) {
                requestIdleCallback(start, { timeout: 1500 });
            } else {
                setTimeout(start, 200);
            }
        });
    }


    /* =====================================================
       2. ETICHETELE „+"

       Apar și dispar continuu, pe poziții alese aleator.
       Trei odată, ca să nu se aglomereze forma. Au voie să
       treacă peste dinte — de-aia sunt pastile cu fundal, nu
       text simplu: peste alb, textul alb ar dispărea.

       Ca să adaugi sau să scoți un beneficiu, editează DOAR
       lista PLUS_TEXT.
       ===================================================== */

    var PLUS_TEXT = [
        "Anestezie fără durere",
        "Radiografie pe loc",
        "Preț spus înainte",
        "Plan de tratament scris",
        "Sterilizare documentată",
        "Garanție scrisă la lucrări",
        "Urgențe în aceeași zi",
        "Același medic, de fiecare dată"
    ];

    /* Fiecare slot = o coloană și cât de sus, în procente din
       înălțimea formei. Zonele evită scobiturile măștii:
         stânga  — abia sub scobitura de sus (35%)
         dreapta — deasupra scobiturii de jos (87%)
         centru  — și una, și alta */
    var PLUS_SLOTS = [
        { side: "left",   top: "44%" },
        { side: "left",   top: "58%" },
        { side: "left",   top: "72%" },
        { side: "left",   top: "84%" },
        { side: "center", top: "6%"  },
        { side: "center", top: "20%" },
        { side: "center", top: "58%" },
        { side: "center", top: "72%" },
        { side: "right",  top: "6%"  },
        { side: "right",  top: "20%" },
        { side: "right",  top: "34%" },
        { side: "right",  top: "48%" },
        { side: "right",  top: "62%" },
        { side: "right",  top: "72%" }
    ];

    var PLUS_SHOWN = 3;    /* câte se văd în același timp */
    var PLUS_FADE = 450;   /* ms — trebuie să fie cât tranziția din CSS */
    var PLUS_GAP = 16;     /* puncte procentuale între două etichete */
    var PLUS_LIFE = 4500;  /* ms cât stă o etichetă pe ecran, minim */

    function startPlusField(field) {
        var live = [];

        function level(slot) { return parseFloat(slot.top); }

        function spawn() {
            /* Un slot e liber dacă nu e ocupat ȘI dacă nu e prea aproape
               pe verticală de altă etichetă. Fără a doua condiție, una
               din stânga și una din centru ajung la aceeași înălțime și
               se suprapun. */
            var slots = PLUS_SLOTS.filter(function (slot) {
                return live.every(function (item) {
                    return item.slot !== slot &&
                           Math.abs(level(item.slot) - level(slot)) >= PLUS_GAP;
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
            el.innerHTML = '<i aria-hidden="true"></i>';
            el.appendChild(document.createTextNode(text));

            field.appendChild(el);

            /* Citirea forțează browserul să calculeze layoutul acum, ca
               tranziția să pornească de la opacity 0 în loc să sară
               direct la 1. Fără ea, eticheta apare instantaneu. */
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
            }, PLUS_LIFE + Math.random() * 3000);
        }

        /* Etichetele statice din HTML există doar pentru cazul „fără
           JS". De aici încolo le construiește codul. */
        field.innerHTML = "";

        for (var i = 0; i < PLUS_SHOWN; i++) {
            setTimeout(spawn, i * 700);
        }
        setInterval(function () {
            if (live.length < PLUS_SHOWN) spawn();
        }, 1400);
    }

    var plusField = document.querySelector("[data-plus]");

    /* Cu „reduce motion" pornit rămân cele trei din HTML, nemișcate. */
    if (plusField && !calm) {
        startPlusField(plusField);
    }


    /* =====================================================
       3. ÎNAINTE / DUPĂ

       Un input range invizibil face toată treaba: merge cu
       mouse, cu deget și cu tastatura, fără să scriem noi
       logica de accesibilitate.
       ===================================================== */

    document.querySelectorAll(".ba").forEach(function (box) {
        var range = box.querySelector(".ba-range");
        if (!range) return;

        var apply = function () {
            box.style.setProperty("--pos", range.value + "%");
        };

        range.addEventListener("input", apply);
        apply();
    });


    /* =====================================================
       4. HARTA

       Se încarcă la cerere. Până apeși, nicio cerere către
       Google și niciun cookie.
       ===================================================== */

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