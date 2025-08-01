/**
 * Polar to Cartesian
 * by Daniel Shiffman.  
 * 
 * Convert a polar coordinate (r,theta) to cartesian (x,y).
 * The calculations are x=r*cos(theta) and y=r*sin(theta).  
 */

float r;

#include "Umfeld.h"

using namespace umfeld;

// Angle and angular velocity, accleration
float theta;
float theta_vel;
float theta_acc;

void settings() {
    size(640, 360);
}

void setup() {
    // Initialize all values
    r         = height * 0.45;
    theta     = 0;
    theta_vel = 0;
    theta_acc = 0.0001;
}

void draw() {

    background(0.f); //@diff(color_range)

    // Translate the origin point to the center of the screen
    translate(width / 2, height / 2);

    // Convert polar to cartesian
    float x = r * cos(theta);
    float y = r * sin(theta);

    // Draw the ellipse at the cartesian coordinate
    ellipseMode(CENTER);
    noStroke();
    fill(0.78f); //@diff(color_range)
    ellipse(x, y, 32, 32);

    // Apply acceleration and velocity to angle
    theta_vel += theta_acc;
    theta += theta_vel;
}
