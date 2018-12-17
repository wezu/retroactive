//GLSL
#version 130
uniform sampler2D tex;
uniform vec3 config;
uniform vec2 screen_size;

flat in vec2 center;
flat in float point_size;
in vec2 uv_offset;

out vec4 fragColor;




void main()
    {
    vec2 screen_uv=gl_FragCoord.xy/screen_size;

    vec2 uv = (gl_FragCoord.xy / screen_size - center) / (point_size / screen_size) + 0.5;
    uv.y-=1.0;
    float frame_size=config.x;
    uv*=frame_size/textureSize(tex,0).x;
    uv+=uv_offset;
    fragColor=texture(tex, uv);
    }
