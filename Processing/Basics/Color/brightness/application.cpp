/**
 * Brightness 
 * by Rusty Robison. 
 * 
 * Brightness is the relative lightness or darkness of a color.
 * Move the cursor vertically over each bar to alter its brightness. 
 */
#include "Umfeld.h"

using namespace umfeld;

int barWidth = 20;
int lastBar  = -1;

uint32_t hsb_to_rgb_packed(const float h, const float s, const float b, const float a = 1.0f) {
    float r = 0, g = 0, bl = 0;
    float hh = h * 6.0f; // h in [0,1] mapped to [0,6]
    int i = static_cast<int>(hh);
    float f = hh - i;
    float p = b * (1.0f - s);
    float q = b * (1.0f - s * f);
    float t = b * (1.0f - s * (1.0f - f));
    switch (i % 6) {
        case 0: r = b; g = t; bl = p; break;
        case 1: r = q; g = b; bl = p; break;
        case 2: r = p; g = b; bl = t; break;
        case 3: r = p; g = q; bl = b; break;
        case 4: r = t; g = p; bl = b; break;
        case 5: r = b; g = p; bl = q; break;
    }
    return static_cast<uint32_t>(a * 255) << 24 |
           static_cast<uint32_t>(bl * 255) << 16 |
           static_cast<uint32_t>(g * 255) << 8 |
           static_cast<uint32_t>(r * 255);
}

void settings() {
    size(640, 360);
}

void setup() {
    noStroke();
    background(0.f); //@diff(color_range)
}

void draw() {
    int whichBar = mouseX / barWidth;
    if (whichBar != lastBar) {
        float barX = whichBar * barWidth;
        uint32_t c = hsb_to_rgb_packed(static_cast<float>(whichBar) / (width / barWidth), 1.0f, mouseY / height);
        fill_color(c);
        rect(barX, 0, barWidth, height);
        lastBar = whichBar;
    }
}