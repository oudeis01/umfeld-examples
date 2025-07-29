/*
 * this example shows how to use `saveFrame()` to save the current frame to a file.
 */

#include "Umfeld.h"
#include "Geometry.h"

using namespace umfeld;

void settings() {
    size(1024, 768);
}

void setup() {
    rectMode(CENTER);
}

void draw() {
    background(0.85f);

    stroke(0.0f);
    fill(0.5f, 0.85f, 1.0f);
    strokeWeight(15);
    strokeJoin(ROUND);
    strokeCap(ROUND);

    pushMatrix();

    translate(width / 2, height / 2);
    rotateY(frameCount * 0.027f);
    rotateZ(frameCount * 0.01f);

    beginShape();
    vertex(-110, -110);
    vertex(110, -110);
    vertex(110, 110);
    vertex(-110, 110);
    endShape(CLOSE);

    popMatrix();

    noStroke();
    fill(1.0f, 0.25f, 0.35f);
    circle(width * 0.5f, height * 0.5f, 55);
}

void keyPressed() {
    if (key == '1') {
        saveFrame();
    }
    if (key == '2') {
        const std::string save_path = selectFolder("Choose a folder");
        if (!save_path.empty()) {
            saveFrame(save_path + "fast-uncompressed-frame.bmp");
        }
    }
}
