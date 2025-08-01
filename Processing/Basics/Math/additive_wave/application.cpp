/**
 * Additive Wave
 * by Daniel Shiffman. 
 * 
 * Create a more complex wave by adding two waves together. 
 */

#include "Umfeld.h"

using namespace umfeld;

int xspacing = 8; // How far apart should each horizontal location be spaced
int w;            // Width of entire wave
int maxwaves = 4; // total # of waves to add together

float              theta = 0.0;
std::vector<float> amplitude(maxwaves); // Height of wave @diff(std::vector)
std::vector<float> dx(maxwaves);        // Value for incrementing X, to be calculated as a function of period and xspacing @diff(std::vector)
std::vector<float> yvalues;             // Using an array to store height values for the wave (not entirely necessary) @diff(std::vector)

void calcWave(); //@diff(foward_declaration)
void renderWave(); //@diff(foward_declaration)

void settings() {
    size(640, 360);
}

void setup() {
    frameRate = 30.0f; //@diff(frameRate)
    // colorMode(RGB, 255, 255, 255, 100);
    w = width + 16;

    for (int i = 0; i < maxwaves; i++) {
        amplitude[i] = random(10, 30);
        float period = random(100, 300); // How many pixels before the wave repeats
        dx[i]        = (TWO_PI / period) * xspacing;
    }

    yvalues = std::vector<float>(w / xspacing); //@diff(std::vector)
}

void draw() {
    background(0.f);
    calcWave();
    renderWave();
}

void calcWave() {
    // Increment theta (try different values for 'angular velocity' here
    theta += 0.02;

    // Set all height values to zero
    for (int i = 0; i < yvalues.size(); i++) {
        yvalues[i] = 0;
    }

    // Accumulate wave height values
    for (int j = 0; j < maxwaves; j++) {
        float x = theta;
        for (int i = 0; i < yvalues.size(); i++) {
            // Every other wave is cosine instead of sine
            if (j % 2 == 0) {
                yvalues[i] += sin(x) * amplitude[j];
            } else {
                yvalues[i] += cos(x) * amplitude[j];
            }
            x += dx[j];
        }
    }
}

void renderWave() {
    // A simple way to draw the wave with an ellipse at each location
    noStroke();
    fill(1.f, .5f); //@diff(color_range)
    ellipseMode(CENTER);
    for (int x = 0; x < yvalues.size(); x++) {
        ellipse(x * xspacing, height / 2 + yvalues[x], 16, 16);
    }
}
