/**
 * Mixture Grid  
 * modified from an example by Simon Greenwold. 
 * 
 * Display a 2D grid of boxes with three different kinds of lights. 
 */


#include "Umfeld.h"

using namespace umfeld;

void defineLights(); //@diff(forward_declaration)

void settings() {
    size(640, 360, RENDERER_OPENGL_3_3_CORE); //@diff(renderer)
}

void setup() {
    noStroke();
}


void draw() {
    defineLights();
    background(0.f); //@diff(color_range)

    for (int x = 0; x <= width; x += 60) {
        for (int y = 0; y <= height; y += 60) {
            pushMatrix();
            translate(x, y);
            rotateY(map(mouseX, 0, width, 0, PI));
            rotateX(map(mouseY, 0, height, 0, PI));
            box(90);
            popMatrix();
        }
    }
}

void defineLights() {
    // FIXME: error: ‘pointLight’ was not declared in this scope
    // Orange point light on the right
    // pointLight(150, 100, 0,   // Color
    //            200, -150, 0); // Position

    // FIXME: error: 'directionalLight' was not declared in this scope
    // Blue directional light from the left
    // directionalLight(0, 102, 255, // Color
    //                  1, 0, 0);    // The x-, y-, z-axis direction

    // FIXME: error: ‘spotLight’ was not declared in this scope
    // spotLight(255, 255, 109, // Color
    //           0, 40, 200,    // Position
    //           0, -0.5, -0.5, // Direction
    //           PI / 2, 2);    // Angle, concentration
}
