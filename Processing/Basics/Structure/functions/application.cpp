/**
 * Functions. 
 * 
 * The drawTarget() function makes it easy to draw many distinct targets. 
 * Each call to drawTarget() specifies the position, size, and number of 
 * rings for each target. 
 */

#include "Umfeld.h"

using namespace umfeld;

void drawTarget(float xloc, float yloc, int size, int num); //@diff(forward_declaration)

void settings() {
    size(640, 360);
}

void setup() {
    background(.2f); //@diff(color_range)
    noStroke();
    noLoop();
}

void draw() {
    drawTarget(width * 0.25, height * 0.4, 200, 4);
    drawTarget(width * 0.5, height * 0.5, 300, 10);
    drawTarget(width * 0.75, height * 0.3, 120, 6);
}

void drawTarget(float xloc, float yloc, int size, int num) {
    float grayvalues = 1.f / (float)num; //@diff(color_range)
    float steps      = size / num;
    for (int i = 0; i < num; i++) {
        fill(i * grayvalues);
        ellipse(xloc, yloc, size - i * steps, size - i * steps);
    }
}
