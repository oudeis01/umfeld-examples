/**
 * Easing. 
 * 
 * Move the mouse across the screen and the symbol will follow.  
 * Between drawing each frame of the animation, the program
 * calculates the difference between the position of the 
 * symbol and the cursor. If the distance is larger than
 * 1 pixel, the symbol moves part of the distance (0.05) from its
 * current position toward the cursor. 
 */

#include "Umfeld.h"

using namespace umfeld;

float x;
float y;
float easing = 0.05;

void settings() {
    size(640, 360);
}

void setup() {
    noStroke();
}

void draw() {
    background(.2f); //@diff(color_range)

    float targetX = mouseX;
    float dx      = targetX - x;
    x += dx * easing;

    float targetY = mouseY;
    float dy      = targetY - y;
    y += dy * easing;

    ellipse(x, y, 66, 66);
}