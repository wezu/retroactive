#version 130
in vec4 p3d_Vertex;
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec2 p3d_MultiTexCoord0;

out vec2 uv;

void main()
    {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uv=p3d_MultiTexCoord0;
    }
