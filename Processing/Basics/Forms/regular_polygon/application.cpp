/**
 * Regular Polygon
 * 
 * What is your favorite? Pentagon? Hexagon? Heptagon? 
 * No? What about the icosagon? The polygon() function 
 * created for this example is capable of drawing any 
 * regular polygon. Try placing different numbers into the 
 * polygon() function calls within draw() to explore. 
 */

#include "Umfeld.h"

using namespace umfeld;

void polygon(float x, float y, float radius, int npoints); //@diff(forward_declaration)

void settings() {
    size(640, 360);
}

void setup() {
    
}

void draw() {
    background(0.4f); //@diff(color_range)

    pushMatrix();
    translate(width * 0.2, height * 0.5);
    rotate(frameCount / 200.0);
    polygon(0, 0, 82, 3); // Triangle
    popMatrix();

    pushMatrix();
    translate(width * 0.5, height * 0.5);
    rotate(frameCount / 50.0);
    polygon(0, 0, 80, 20); // Icosagon
    popMatrix();

    pushMatrix();
    translate(width * 0.8, height * 0.5);
    rotate(frameCount / -100.0);
    polygon(0, 0, 70, 7); // Heptagon
    popMatrix();
}

void polygon(float x, float y, float radius, int npoints) {
    float angle = TWO_PI / npoints;
    beginShape();
    for (float a = 0; a < TWO_PI; a += angle) {
        float sx = x + cos(a) * radius;
        float sy = y + sin(a) * radius;
        vertex(sx, sy);
    }
    endShape(CLOSE);
}