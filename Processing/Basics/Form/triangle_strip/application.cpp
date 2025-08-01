/**
 * Triangle Strip 
 * by Ira Greenberg. 
 * 
 * Generate a closed ring using the vertex() function and 
 * beginShape(TRIANGLE_STRIP) mode. The outsideRadius and insideRadius 
 * variables control ring's radii respectively.
 */

#include "Umfeld.h"

using namespace umfeld;

int   x;
int   y;
float outsideRadius = 150;
float insideRadius  = 100;

void settings() {
    size(640, 360);
}

void setup() {
    background(0.8f); //@diff(color_range)
    x = width / 2;
    y = height / 2;
}

void draw() {
    background(0.8f); //@diff(color_range)

    int   numPoints = int(map(mouseX, 0, width, 6, 60));
    float angle     = 0;
    float angleStep = 180.0 / numPoints;

    beginShape(TRIANGLE_STRIP);
    for (int i = 0; i <= numPoints; i++) {
        float px = x + cos(radians(angle)) * outsideRadius;
        float py = y + sin(radians(angle)) * outsideRadius;
        angle += angleStep;
        vertex(px, py);
        px = x + cos(radians(angle)) * insideRadius;
        py = y + sin(radians(angle)) * insideRadius;
        vertex(px, py);
        angle += angleStep;
    }
    endShape();
}
