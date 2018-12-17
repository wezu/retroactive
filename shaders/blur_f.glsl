//GLSL
#version 140
uniform sampler2D tex;
uniform float blur;

in vec2 uv;

void main()
    {
    vec2 pixel = vec2(1.0, 1.0)/textureSize(tex, 0).xy;
    vec2 sharp=pixel*blur;

    vec4 out_tex= texture(tex, uv);
    //Hardcoded blur
    out_tex += texture(tex, uv+vec2(-0.326212,-0.405805)*sharp);
    out_tex += texture(tex, uv+ vec2(-0.840144, -0.073580)*sharp);
    out_tex += texture(tex, uv+vec2(-0.695914,0.457137)*sharp);
    out_tex += texture(tex, uv+vec2(-0.203345,0.620716)*sharp);
    out_tex += texture(tex, uv+vec2(0.962340,-0.194983)*sharp);
    out_tex += texture(tex, uv+vec2(0.473434,-0.480026)*sharp);
    out_tex += texture(tex, uv+vec2(0.519456,0.767022)*sharp);
    out_tex += texture(tex, uv+vec2(0.185461,-0.893124)*sharp);
    out_tex += texture(tex, uv+vec2(0.507431,0.064425)*sharp);
    out_tex += texture(tex, uv+vec2(0.896420,0.412458)*sharp);
    out_tex += texture(tex, uv+vec2(-0.321940,-0.932615)*sharp);
    out_tex += texture(tex, uv+vec2(-0.791559,-0.597705)*sharp);
    out_tex/=13.0;



    gl_FragData[0] = out_tex;
    }

