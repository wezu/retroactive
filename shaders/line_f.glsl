#version 130
uniform vec4 color;

in vec3 world_pos;
in float view_z;

out vec4 fragColor;

void main()
    {
    float sawtooth =smoothstep(0.6, 1.0, mod((world_pos.z-0.2)*4.3, 1.3));
    float triangle = abs(2.0 * sawtooth-1.0);
    float dp = length(vec2(dFdx(world_pos.z), dFdy(world_pos.z)));
    float edge = dp * 10.0;
    float square = 1.0-smoothstep(0.5 - edge, 0.5 + edge, triangle);

    //sawtooth =smoothstep(0.6, 1.0, mod(world_pos.y*4.3, 1.3));
    //triangle = abs(2.0 * sawtooth-1.0);
    //dp = length(vec2(dFdx(world_pos.y), dFdy(world_pos.y)));
    //edge = dp * 10.0;
    //square += 1.0-smoothstep(0.5 - edge, 0.5 + edge, triangle);


    vec4 final_color=mix(color, vec4(0.0, 0.0, 0.0, 1.0), pow(view_z*0.01, 2.0))*square;
    final_color.a=color.a;
    fragColor =final_color;
    }
