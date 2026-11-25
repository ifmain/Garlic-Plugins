#include "garlic.h"

/* Simulation coordinates are in 1/1000 logical pixels. No libc or OS imports. */
static GarlicFrame scene;
static int ball_x=160000, ball_y=120000, vx=148, vy=79;
static int left=98, right=98, player_score, cpu_score, paused_ms=400;
static int clamp(int n,int lo,int hi){return n<lo?lo:n>hi?hi:n;}
static void rect(int x,int y,int w,int h,int color){
    scene.rectangles[scene.count++]=(GarlicRect){x,y,w,h,color};
}
static void serve(int direction){
    ball_x=160000;ball_y=120000;vx=direction*148;
    vy=((player_score+cpu_score)%2?1:-1)*79;paused_ms=650;
}
static void step(int ms){
    int target=clamp(ball_y/1000-22,5,191);
    int maximum=(ms*105+500)/1000;
    right+=clamp(target-right,-maximum,maximum);
    if(paused_ms>0){paused_ms-=ms;return;}
    int previous=ball_x;
    ball_x+=vx*ms;ball_y+=vy*ms;
    if(ball_y<5000){ball_y=10000-ball_y;vy=-vy;}
    if(ball_y>235000){ball_y=470000-ball_y;vy=-vy;}
    int y=ball_y/1000;
    if(vx<0 && previous>=21000 && ball_x<=21000 && y>=left-3 && y<=left+47){
        vx=clamp(-vx+9,148,300);ball_x=21000;vy=clamp((y-left-22)*7,-170,170);
    }
    if(vx>0 && previous<=299000 && ball_x>=299000 && y>=right-3 && y<=right+47){
        vx=-clamp(vx+9,148,300);ball_x=299000;vy=clamp((y-right-22)*7,-170,170);
    }
    if(ball_x<0){cpu_score=(cpu_score+1)%10;serve(1);}
    if(ball_x>320000){player_score=(player_score+1)%10;serve(-1);}
}
static void digit(int x,int value){
    static const unsigned char masks[]={63,6,91,79,102,109,125,7,127,111};
    static const int bars[7][4]={{2,0,8,2},{10,2,2,7},{10,11,2,7},{2,18,8,2},{0,11,2,7},{0,2,2,7},{2,9,8,2}};
    for(int i=0;i<7;i++)if(masks[value]&(1<<i))rect(x+bars[i][0],12+bars[i][1],bars[i][2],bars[i][3],0xb1cad5);
}
GarlicFrame *ui_frame(int32_t x,int32_t y,int32_t pressed,int32_t elapsed_ms){
    (void)x;
    if(pressed) left=clamp(y-22,5,191);
    for(int ms=elapsed_ms;ms>0;){int slice=ms>16?16:ms;step(slice);ms-=slice;}
    scene.count=0;rect(0,0,320,240,0x101c26);
    for(int j=4;j<240;j+=14)rect(159,j,2,7,0x2a414b);
    digit(132,player_score);digit(176,cpu_score);
    rect(13,left,5,44,0x60ead0);rect(302,right,5,44,0xffb782);
    rect(ball_x/1000-3,ball_y/1000-3,6,6,0xf6f7f5);
    return &scene;
}
