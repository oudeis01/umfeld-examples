/**
 * Recursion. 
 * 
 * A demonstration of recursion, which means functions call themselves. 
 * Notice how the drawCircle() function calls itself at the end of its block. 
 * It continues to do this until the variable "level" is equal to 1. 
 */
#include "Umfeld.h"

using namespace umfeld;

void drawCircle(int x, int radius, int level); //@diff(forward_declaration)

void settings() {
    size(640, 360);
}

void setup() {
    noStroke();
    noLoop();
}

void draw() {
    drawCircle(width / 2, 280, 6);
}

void drawCircle(int x, int radius, int level) {
    float tt = 126 * level / 4.0;
    fill(tt / 255.f); //@diff(color_range)
    ellipse(x, height / 2, radius * 2, radius * 2);
    if (level > 1) {
        level = level - 1;
        drawCircle(x - radius / 2, radius / 2, level);
        drawCircle(x + radius / 2, radius / 2, level);
    }
}
