/**
 * Bezier. 
 * 
 * The first two parameters for the bezier() function specify the 
 * first point in the curve and the last two parameters specify 
 * the last point. The middle parameters set the control points
 * that define the shape of the curve. 
 */
#include "Umfeld.h"

using namespace umfeld;

void settings() {
    size(640, 360);
}

void setup() {
    stroke(1.f); //@diff(color_range)
    noFill();
}

void draw() {
    background(0.f); //@diff(color_range)
    for (int i = 0; i < 200; i += 20) {
        bezier(mouseX - (i / 2.0), 40 + i, 410, 20, 440, 300, 240 - (i / 16.0), 300 + (i / 8.0));
    }
}
