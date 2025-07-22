/**
 * Radial Gradient. 
 * 
 * Draws a series of concentric circles to create a gradient 
 * from one color to another.
 */

#include "Umfeld.h"

using namespace umfeld;

int dim;

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

void drawGradient(float x, float y) {
    int   radius = dim / 2;
    float h      = random(0, 360);

    for (int r = radius; r > 0; --r) {
        uint32_t hsbColor = hsb_to_rgb_packed(h/360.f, 0.9f, 0.9f);
        fill_color(hsbColor); //@diff(fill_color)
        ellipse(x, y, r, r);
        h = (int)(h + 1) % 360;
    }
}

void settings() {
    size(640, 360);
}

void setup() {
    dim = width / 2;
    background(0.f); //@diff(color_range)
    noStroke();
    ellipseMode(RADIUS);
    set_frame_rate(1.f); //@diff(frameRate)
}


void draw() {
    background(0.f); //@diff(color_range)
    for (int x = 0; x <= width; x += dim) {
        drawGradient(x, height / 2);
    }
}
