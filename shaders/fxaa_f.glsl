//GLSL
#version 130
//#extension GL_EXT_gpu_shader4 : enable

uniform sampler2D pre_aa; // 0
uniform float span_max = 8.0;
uniform float reduce_mul = 1.0/8.0;
uniform float reduce_min = 1.0/128.0;
in vec4 uv;
out vec4 final_color;


vec3 FxaaPixelShader(
  vec4 uv, // Output of FxaaVertexShader interpolated across screen.
  sampler2D tex, // Input texture.
  vec2 rcpFrame) // Constant {1.0/frameWidth, 1.0/frameHeight}.
{
/*---------------------------------------------------------*/
    vec3 rgbNW = textureLod(tex, uv.xy, 0.0).xyz;
    vec3 rgbNE = textureLodOffset(tex, uv.zw+rcpFrame.xy, 0.0, ivec2(1,0)).xyz;
    vec3 rgbSW = textureLodOffset(tex, uv.zw+rcpFrame.xy, 0.0, ivec2(0,1)).xyz;
    vec3 rgbSE = textureLodOffset(tex, uv.zw+rcpFrame.xy, 0.0, ivec2(1,1)).xyz;
    vec3 rgbM  = textureLod(tex, uv.xy, 0.0).xyz;
/*---------------------------------------------------------*/
    vec3 luma = vec3(0.299, 0.587, 0.114);
    float lumaNW = dot(rgbNW, luma);
    float lumaNE = dot(rgbNE, luma);
    float lumaSW = dot(rgbSW, luma);
    float lumaSE = dot(rgbSE, luma);
    float lumaM  = dot(rgbM,  luma);
/*---------------------------------------------------------*/
    float lumaMin = min(lumaM, min(min(lumaNW, lumaNE), min(lumaSW, lumaSE)));
    float lumaMax = max(lumaM, max(max(lumaNW, lumaNE), max(lumaSW, lumaSE)));
/*---------------------------------------------------------*/
    vec2 dir;
    dir.x = -((lumaNW + lumaNE) - (lumaSW + lumaSE));
    dir.y =  ((lumaNW + lumaSW) - (lumaNE + lumaSE));
/*---------------------------------------------------------*/
    float dirReduce = max(
        (lumaNW + lumaNE + lumaSW + lumaSE) * (0.25 * reduce_mul),
        reduce_min);
    float rcpDirMin = 1.0/(min(abs(dir.x), abs(dir.y)) + dirReduce);
    dir = min(vec2( span_max,  span_max),
          max(vec2(-span_max, -span_max),
          dir * rcpDirMin)) * rcpFrame.xy;
/*--------------------------------------------------------*/
    vec3 rgbA = (1.0/2.0) * (
        textureLod(tex, uv.xy + dir * (1.0/3.0 - 0.5), 0.0).xyz +
        textureLod(tex, uv.xy + dir * (2.0/3.0 - 0.5), 0.0).xyz);
    vec3 rgbB = rgbA * (1.0/2.0) + (1.0/4.0) * (
        textureLod(tex, uv.xy + dir * (0.0/3.0 - 0.5), 0.0).xyz +
        textureLod(tex, uv.xy + dir * (3.0/3.0 - 0.5), 0.0).xyz);
    float lumaB = dot(rgbB, luma);
    if((lumaB < lumaMin) || (lumaB > lumaMax))
        return rgbA;
    return rgbB;
}


void main()
{
  final_color = vec4(0.0);
  vec2 win_size=textureSize(pre_aa, 0).xy;
  vec2 rcpFrame = vec2(1.0/win_size.x, 1.0/win_size.y);
  final_color.rgb = FxaaPixelShader(uv, pre_aa, rcpFrame);
}
