//GLSL
#version 130
uniform sampler2D input_tex;
uniform sampler2D beat_tex;
uniform vec2 beat_uv;
uniform float osg_FrameTime;

in vec2 uv;

out vec4 fragColor;

void main()
    {
    vec2 res=textureSize(input_tex, 0).xy;
    vec3 beat=vec3(1.0)+texture(beat_tex, beat_uv).rgb;
    vec2 pixel = vec2(1.0)/res;

    vec3 chroma_distort = vec3(-3.75, 2.5, 7.5)*beat*pow(0.1+distance(uv, vec2(0.5, 0.5)), 2.0);

    // cromatic distort:
    fragColor = vec4(0.0, 0.0, 0.0, 1.0);
    fragColor.r = texture(input_tex, uv +uv*pixel* chroma_distort.x).r;
    fragColor.g = texture(input_tex, uv +uv*pixel* chroma_distort.y).g;
    fragColor.b = texture(input_tex, uv +uv*pixel* chroma_distort.z).b;
    //beat to color
    fragColor.rgb*=clamp(beat, vec3(1.0), vec3(1.9));
    }

