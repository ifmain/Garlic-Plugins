#include "garlic.h"

static uint8_t buf[8192], response[8192];
static char host[256], user[256], pass[256];
static int port, phase, received, size;
enum { HTTP, SOCKS4, METHOD, AUTH, CONNECT };
uint8_t *net_buffer(void) { return buf; }
int32_t route_next(int32_t primary,int32_t additional,int32_t attempt) {
    if (additional && !attempt) return GARLIC_ADDITIONAL;
    return primary ? GARLIC_PRIMARY : additional ? GARLIC_ADDITIONAL : GARLIC_CONTINUE;
}
static int length(const char *s) {int n=0;while(s[n])n++;return n;}
static int same(const char *s,const char *t){while(*s && *s==*t){s++;t++;}return *s==*t;}
static void copy(char *d,const char *s){while((*d++=*s++)){}}
static void byte(int b){buf[size++]=(uint8_t)b;}
static void text(const char *s){while(*s)byte(*s++);}
static void string8(const char *s){byte(length(s));text(s);}
static void send_port(void){byte(port>>8);byte(port);}
static void basic(void){
    static const char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    char raw[512];int n=length(user);copy(raw,user);raw[n++]=':';copy(raw+n,pass);n+=length(pass);
    for(int i=0;i<n;i+=3){
        unsigned a=(uint8_t)raw[i]<<16;
        if(i+1<n)a|=(uint8_t)raw[i+1]<<8;
        if(i+2<n)a|=(uint8_t)raw[i+2];
        byte(alphabet[a>>18]);byte(alphabet[(a>>12)&63]);
        byte(i+1<n?alphabet[(a>>6)&63]:'=');byte(i+2<n?alphabet[a&63]:'=');
    }
}
static int open_stream(int n){
    char *fields[4];int pos=0;
    for(int i=0;i<4;i++){
        fields[i]=(char*)buf+pos;while(pos<n && buf[pos])pos++;
        if(pos++>=n)return -1;
    }
    if(pos!=n || length(fields[2])>255 || length(fields[3])>255)return -1;
    if(same(fields[0],"ssh"))return GARLIC_READY;
    int http=same(fields[0],"http")||same(fields[0],"https");
    int four=same(fields[0],"socks4");
    if(!http && !four && !same(fields[0],"socks5"))return -1;
    char authority[320];if(length(fields[1])>=320)return -1;
    copy(authority,fields[1]);copy(user,fields[2]);copy(pass,fields[3]);
    if(http){
        phase=HTTP;text("CONNECT ");text(authority);text(" HTTP/1.1\r\nHost: ");text(authority);
        if(*user){text("\r\nProxy-Authorization: Basic ");basic();}
        text("\r\n\r\n");return size;
    }
    int colon=length(authority);while(colon && authority[colon]!=':')colon--;
    if(!colon)return -1;
    for(char *p=authority+colon+1;*p;p++){
        if(*p<'0'||*p>'9')return -1;
        port=port*10+(*p-'0');if(port>65535)return -1;
    }
    authority[colon]=0;char *h=authority;
    if(*h=='[' && colon>=2 && authority[colon-1]==']'){h++;authority[colon-1]=0;}
    if(!*h || length(h)>255 || !port)return -1;
    copy(host,h);
    if(four){
        phase=SOCKS4;byte(4);byte(1);send_port();byte(0);byte(0);byte(0);byte(1);
        text(user);byte(0);text(host);byte(0);
    }else{phase=METHOD;byte(5);byte(1);byte(*user?2:0);}
    return size;
}
static int connect5(void){
    phase=CONNECT;received=0;
    byte(5);byte(1);byte(0);byte(3);string8(host);send_port();return size;
}
int32_t net_step(int32_t event,int32_t n){
    size=0;
    if(event==GARLIC_OPEN)return open_stream(n);
    if(event==GARLIC_APP_DATA || event==GARLIC_PEER_DATA)return n;
    if(event==GARLIC_APP_EOF || event==GARLIC_PEER_EOF)return 0;
    if(event!=GARLIC_HANDSHAKE || n!=1 || received>=8192)return -1;
    response[received++]=buf[0];
    switch(phase){
    case HTTP:
        if(received<4 || response[received-4]!='\r'||response[received-3]!='\n'||
           response[received-2]!='\r'||response[received-1]!='\n')return 0;
        return received>=16 && response[0]=='H' && response[1]=='T' && response[2]=='T' &&
            response[3]=='P' && response[4]=='/' && response[8]==' ' && response[9]=='2' &&
            response[10]=='0' && response[11]=='0' && (response[12]==' '||response[12]=='\r')?GARLIC_READY:-1;
    case SOCKS4:
        return received<8?0:response[0]==0 && response[1]==90?GARLIC_READY:-1;
    case METHOD:
        if(received<2)return 0;
        if(response[0]!=5 || response[1]!=(*user?2:0))return -1;
        if(!*user)return connect5();
        phase=AUTH;received=0;byte(1);string8(user);string8(pass);return size;
    case AUTH:
        if(received<2)return 0;
        if(response[0]!=1||response[1])return -1;
        return connect5();
    case CONNECT:
        if(received<4)return 0;
        if(response[0]!=5||response[1]||response[2])return -1;
        int type=response[3];if(type==3 && received<5)return 0;
        int count=type==1?10:type==4?22:type==3?7+response[4]:-1;
        return count<0?-1:received==count?GARLIC_READY:0;
    default:return -1;
    }
}
