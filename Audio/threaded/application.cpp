/*
 * this example demonstrates how to load a sample and apply a low pass filter
 * to it. it also shows how to resample a sample to a different sample rate.
 */

#include "Umfeld.h"
#include "audio/Sampler.h"
#include "audio/LowPassFilter.h"

using namespace umfeld;

Sampler*       sampler;
LowPassFilter* filter;

void settings() {
    size(1024, 768);
    AudioUnitInfo info;
    info.input_channels  = 0;
    info.output_channels = 2;
    info.threaded        = true;
    audio(info);
    /* select audio subsystem */
    // subsystem_audio = umfeld_create_subsystem_audio_sdl(); // default
    // subsystem_audio = umfeld_create_subsystem_audio_portaudio();
}

void setup() {
    sampler = loadSample("teilchen.wav");

    const float sampler_sample_rate = sampler->get_sample_rate();
    filter                          = new LowPassFilter(sampler_sample_rate);

    sampler->set_looping();
    sampler->play();
}

void draw() {
    console_once("Draw Thread ID    :", pthread_self());
    background(0.85f);
    noFill();
    stroke(1.0f, 0.25f, 0.35f);
    const float size = 50.0f;
    const float x    = width / 2.0f;
    const float y    = height / 2.0f;
    line(x - size, y - size, x + size, y + size);
    line(x - size, y + size, x + size, y - size);

    filter->set_frequency(map(mouseX, 0, width, 20.0f, 8000.0f));
    filter->set_resonance(map(mouseY, 0, height, 0.1f, 0.9f));
}

void audioEvent() {
    console_once("Audio Thread ID   :", pthread_self());
    float sample_buffer[audio_buffer_size];
    for (int i = 0; i < audio_buffer_size; i++) {
        float sample     = sampler->process();
        sample           = filter->process(sample);
        sample_buffer[i] = sample;
    }
    merge_interleaved_stereo(sample_buffer, sample_buffer, audio_output_buffer, audio_buffer_size);
}

void shutdown() {
    delete sampler;
    delete filter;
}