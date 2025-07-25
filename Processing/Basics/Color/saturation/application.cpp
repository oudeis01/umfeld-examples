/**
 * Saturation. 
 * 
 * Saturation is the strength or purity of the color and represents the 
 * amount of gray in proportion to the hue. A "saturated" color is pure 
 * and an "unsaturated" color has a large percentage of gray. 
 * Move the cursor vertically over each bar to alter its saturation. 
 */
#include "Umfeld.h"

using namespace umfeld;

int barWidth = 20;
int lastBar  = -1;

uint32_t hsb_to_rgb_packed(const float h, const float s, const float b, const float a = 1.0f) {
    const float H = std::clamp(h, 0.0f, 1.0f);
    const float S = std::clamp(s, 0.0f, 1.0f);
    const float V = std::clamp(b, 0.0f, 1.0f);
    const float A = std::clamp(a, 0.0f, 1.0f);

    float r = 0, g = 0, bl = 0;
    float hh = H * 6.0f;         // hue slice
    int   i  = static_cast<int>(hh);
    float f  = hh - i;
    float p  = V * (1.0f - S);
    float q  = V * (1.0f - S * f);
    float t  = V * (1.0f - S * (1.0f - f));

    switch (i % 6) {
        case 0: r = V;  g = t;  bl = p; break;
        case 1: r = q;  g = V;  bl = p; break;
        case 2: r = p;  g = V;  bl = t; break;
        case 3: r = p;  g = q;  bl = V; break;
        case 4: r = t;  g = p;  bl = V; break;
        case 5: r = V;  g = p;  bl = q; break;
    }
    return (static_cast<uint32_t>(A * 255) << 24) |
           (static_cast<uint32_t>(bl * 255) << 16) |
           (static_cast<uint32_t>(g  * 255) <<  8) |
            static_cast<uint32_t>(r  * 255);
}

void settings() {
    size(640, 360);
}

void setup() {
    // colorMode(HSB, width, height, 100);
    noStroke();
}

void draw() {
    int whichBar = mouseX / barWidth;
    if (whichBar != lastBar) {
        float barX = whichBar * barWidth;
        uint32_t c = hsb_to_rgb_packed(barX/width, mouseY / height, .25f);
        fill_color(c);
        glm::vec4 C;
        color_unpack(c, C.r, C.g, C.b, C.a);
        lastBar = whichBar;
    }
}