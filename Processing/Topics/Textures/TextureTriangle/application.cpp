/**
 * Texture Triangle. 
 * 
 * Using a rectangular image to map a texture onto a triangle.
 */

#include "Umfeld.h"

using namespace umfeld;

PImage* img;

void settings() {
    size(640, 360, RENDERER_OPENGL_3_3_CORE); //@diff(renderer)
}

void setup() {
    img = loadImage("berlin-1.jpg");
    noStroke();
}

void draw() {
    background(0.f); //@diff(color_range)
    translate(width / 2, height / 2, 0);
    rotateY(map(mouseX, 0, width, -PI, PI));
    texture(img);
    beginShape();
    vertex(-100, -100, 0, 0, 0);
    vertex(100, -40, 0, 300, 120);
    vertex(0, 100, 0, 200, 400);
    endShape();
}
