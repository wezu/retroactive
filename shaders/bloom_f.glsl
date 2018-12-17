#version 130
uniform sampler2D base_tex;
uniform sampler2D blur_tex;
//uniform sampler2D spec_tex;
//uniform vec2 spec_uv;

in vec2 uv;

out vec4 fragColor;

void main()
    {
    vec3 color=texture(base_tex, uv).rgb+pow((texture(blur_tex, uv).rgb-0.1)*1.5, vec3(2.0));
    //color*=vec3(1.0)+texture(spec_tex, spec_uv).rgb*2.0;
    fragColor =vec4(color.rgb, 1.0);
    }
