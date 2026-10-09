// ═══ Claudio Player · 施工图 Layer 4 ═══
// PWA · 三视图 (Player/Profile/Settings) · 单 audio · WS 流式 · SW 缓存 · prefetch 10s

// ★ 强制清除所有 SW 缓存，确保加载最新代码
if("serviceWorker" in navigator){
    navigator.serviceWorker.getRegistrations().then(function(regs){
        regs.forEach(function(r){r.unregister();});
    });
    caches.keys().then(function(names){names.forEach(function(n){caches.delete(n);});});
}

// ── Clock ──
(function(){
    var te=document.getElementById("time"),we=document.getElementById("weekday"),
        de=document.getElementById("date"),
        dys=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],
        mos=["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];
    function tick(){
        var n=new Date();
        te.textContent=n.toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit"});
        we.textContent=dys[n.getDay()];
        de.textContent=("0"+n.getDate()).slice(-2)+" "+mos[n.getMonth()]+" "+n.getFullYear();
    }
    tick();setInterval(tick,15000);
})();

// ── Avatar: double-click minimize / right-click quit ──
(function(){
    var avatar = document.querySelector(".nav-avatar");
    if (avatar) {
        avatar.style.cursor = "pointer";
        avatar.title = "双击最小化 | 右键退出";
        avatar.addEventListener("dblclick", function(){
            try { window.pywebview.api.minimize(); } catch(e) {}
        });
        avatar.addEventListener("contextmenu", function(e){
            e.preventDefault();
            try { window.pywebview.api.quit(); } catch(e) {}
        });
    }
})();

// ── Theme Toggle ──
(function(){
    var root=document.getElementById("appRoot");
    root.setAttribute("data-theme","dark");
    document.querySelectorAll(".toggle-opt").forEach(function(o){
        o.addEventListener("click",function(){
            document.querySelectorAll(".toggle-opt").forEach(function(x){x.classList.remove("active");});
            o.classList.add("active");root.setAttribute("data-theme",o.dataset.theme);
        });
    });
})();

// ── Tabs (3 views per 施工图: Player / Profile / Settings) ──
// ── Page Nav ──
(function(){
    var track=document.getElementById("sliderTrack"),cur=1;
    var pos=["0%","-50%"];
    var navL=document.getElementById("navLeft"),navR=document.getElementById("navRight");
    var labels=[["","CLAUDIO DJ"],["CLAUDIO FM",""]];
    function slideTo(i){
        cur=i;track.style.transform="translateX("+pos[i]+")";
        navL.textContent=labels[i][0];navR.textContent=labels[i][1];
        var header=document.getElementById("headerTime");
        if(header)header.style.display=i===0?"none":"";
        var login=document.getElementById("navLogin");
        var toggle=document.getElementById("themeToggle");
        var time=document.getElementById("navTime");
        var navBar=document.querySelector(".nav-bar");
        var bottomBar=document.querySelector(".bottom-bar");
        if(i===0){
            if(login)login.style.display="none";
            if(toggle)toggle.style.display="none";
            if(time)time.style.display="inline";
            if(navBar){navBar.style.background="#000";navBar.style.paddingTop="14px";}
            if(bottomBar)bottomBar.style.background="#fff";
            var brand=document.querySelector(".nav-brand-wrap");
            if(brand)brand.style.marginTop="6px";
            updateNavTime();
            // FM no longer auto-starts
            var fsb=document.getElementById("fmStatusBar");
            if(fsb){fsb.style.display="flex";fsb.style.marginTop="6px";}
        }else{
            if(login)login.style.display="";
            if(toggle)toggle.style.display="";
            if(time)time.style.display="none";
            var fsb2=document.getElementById("fmStatusBar");
            if(fsb2)fsb2.style.display="none";
            if(navBar){navBar.style.background="";navBar.style.paddingTop="";}
            var brand2=document.querySelector(".nav-brand-wrap");
            if(brand2)brand2.style.marginTop="";
            if(bottomBar)bottomBar.style.background="";
        }
    }
    function updateNavTime(){
        var time=document.getElementById("navTime");
        if(!time)return;
        var n=new Date();
        time.textContent=n.toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit"});
    }
    setInterval(updateNavTime,15000);
    window.slideTo=slideTo;
    navL.addEventListener("click",function(){if(cur>0)slideTo(cur-1);});
    navR.addEventListener("click",function(){if(cur<1)slideTo(cur+1);});
})();

// ── Queue ──
(function(){
    var bar=document.getElementById("queueBar"),list=document.getElementById("queueList"),
        chev=document.getElementById("queueChevron"),count=document.getElementById("queueCount"),
        open=false,tracks=[];

    bar.addEventListener("click",function(){
        open=!open; chev.classList.toggle("open",open); list.classList.toggle("hidden",!open);
    });

    window.queueAdd=function(name,artist,url,songId,cover){
        tracks.push({name:name,artist:artist,url:url,songId:songId||0,cover:cover||""});
        render();
    };
    window.queueRemove=function(i){
        tracks.splice(i,1); render();
    };
    window.queueClear=function(){tracks=[];render();};
    window.queueNext=function(){
        if(tracks.length){var t=tracks.shift();render();return t;}
        return null;
    };
    window.queueEmpty=function(){return tracks.length===0;};

    // 从后端拉取 AI 推荐，填入队列 + 显示 DJ 说了什么
    window.fetchNext=function(){
        var status=document.getElementById("statusState");
        var dot=document.getElementById("statusDot");
        if(status)status.textContent="FETCHING";
        if(dot)dot.className="status-dot online";
        fetch("/api/next").then(function(r){return r.json();}).then(function(d){
            if(d.next&&d.next.length){
                // 显示 DJ 的选歌思路
                if(d.say&&window.typeReply) window.typeReply(d.say,2000);
                d.next.forEach(function(s){
                    window.queueAdd(s.name,s.artist,s.url,s.id||0,s.cover||"");
                });
                if(!window.currentTrack||!window.currentTrack.url){
                    var first=window.queueNext();
                    if(first&&first.url){
                        if(window.addSystemMsg) window.addSystemMsg("Now playing:"+ first.artist+" — "+first.name);
                        window.playSong(first.url,first.name,first.artist,first.songId,first.cover||"");
                    }
                }
            }
            var wsConnected=window.wsConnected||false;
            if(status)status.textContent=wsConnected?"LIVE":"STANDBY";
            if(dot)dot.className="status-dot "+(wsConnected?"online":"offline");
        }).catch(function(){
            if(status)status.textContent="STANDBY";
            if(dot)dot.className="status-dot offline";
        });
    };

    function render(){
        count.textContent=tracks.length;
        var h="";
        tracks.forEach(function(t,i){
            h+='<div class="queue-item">'
                +'<div class="queue-item-info">'
                +'<div class="queue-item-name">'+esc(t.name)+'</div>'
                +'<div class="queue-item-artist">'+esc(t.artist)+'</div>'
                +'</div>'
                +'<button class="queue-item-remove" data-idx="'+i+'" type="button">×</button>'
                +'</div>';
        });
        list.innerHTML=h;
        list.querySelectorAll(".queue-item").forEach(function(item,i){
            var track=tracks[i];
            item.addEventListener("click",function(e){
                if(e.target.closest(".queue-item-remove"))return;
                if(!track||!track.url)return;
                // Find current index of this track (may have shifted)
                var idx=tracks.indexOf(track);
                if(idx<0)idx=0;
                var t=tracks.splice(idx,1)[0];
                render();
                window.playSong(t.url,t.name,t.artist,t.songId,t.cover||"");
            });
        });
        list.querySelectorAll(".queue-item-remove").forEach(function(b){
            b.addEventListener("click",function(e){
                e.stopPropagation();
                window.queueRemove(parseInt(this.dataset.idx));
            });
        });
    }
    function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
})();

// ── Audio + Prefetch ──
(function(){
    var audio=document.getElementById("audioPlayer"),
        prefetch=document.getElementById("prefetchPlayer"),
        volSlider=document.getElementById("volSlider"),
        bars=document.getElementById("audioBars"),
        prefetchUrl=null,
        _abortId=0;

    volSlider.value=60;
    audio.volume=0.6;
    volSlider.addEventListener("input",function(){audio.volume=this.value/100;});

    window.currentTrack=null;
    window.playHistory=[];

    window.playSong=function(url,name,artist,songId,cover){
        if(!url)return;
        var myId=++_abortId;
        // Stop current playback immediately
        audio.pause(); audio.src="";
        if(window.currentTrack&&window.currentTrack.url && window.currentTrack.url!==url){
            window.playHistory.push(window.currentTrack);
            if(window.playHistory.length>50)window.playHistory.shift();
        }
        songId=songId||0;cover=cover||"";
        window.currentTrack={url:url,name:name,artist:artist,songId:songId,cover:cover};
        var tn=document.getElementById("trackName");
        tn.classList.add("true-focus","blurring");
        setTimeout(function(){
            tn.textContent=name||"";
            tn.classList.remove("blurring");
        },300);
        document.getElementById("trackArtist").textContent=artist||"";
        document.getElementById("playIcon").innerHTML='<rect x="4" y="3" width="5" height="18"/><rect x="15" y="3" width="5" height="18"/>';
        bars.classList.add("playing");
        updateLikeBtnState(songId);
        updateFmDisplay();
        document.getElementById("cardAura").classList.add("playing");

        // Use <audio> for fast streaming playback
        audio.src=url;
        audio.play().then(function(){
            if(myId!==_abortId){audio.pause();return;}
        }).catch(function(e){console.log("playSong err:",e);});

        clearTimeout(window._prefetchTimer);
        window._prefetchTimer=setTimeout(function(){
            if(prefetchUrl&&prefetchUrl!==url) prefetch.src=prefetchUrl;
        },10000);
    };

    // Auto-advance on track end
    audio.addEventListener("ended",function(){
        bars.classList.remove("playing");
        document.getElementById("cardAura").classList.remove("playing");
        window.currentTrack=null;
        var next=window.queueNext();
        if(next&&next.url){window.playSong(next.url,next.name,next.artist,next.songId,next.cover||"");}
        else if(window.queueEmpty()){window.fetchNext();}
        else{document.getElementById("playIcon").innerHTML='<polygon points="5,3 20,12 5,21"/>';}
    });

    audio.addEventListener("pause",function(){
        bars.classList.remove("playing");
        document.getElementById("cardAura").classList.remove("playing");
    });
    audio.addEventListener("play",function(){
        bars.classList.add("playing");
        document.getElementById("cardAura").classList.add("playing");
    });

    function updateFmDisplay(){
        var ct=window.currentTrack;
        var el=document.getElementById("fmEpSong");
        if(el){
            if(ct&&ct.name){el.textContent=ct.artist?ct.artist+" — "+ct.name:ct.name;}
            else{el.textContent="—";}
        }
    }

    window.isMusicPlaying=function(){return !audio.paused;};

    function updateLikeBtnState(songId){
        var lb=document.getElementById("likeBtn");
        if(songId){
            fetch("/api/liked/"+songId).then(function(r){return r.json();}).then(function(d){
                if(d.liked){lb.classList.add("liked");}else{lb.classList.remove("liked");}
            }).catch(function(){});
        }else{lb.classList.remove("liked");}
    }

    window.stopMusic=function(){
        audio.pause(); audio.src="";
        window.currentTrack=null;
        bars.classList.remove("playing");
        document.getElementById("cardAura").classList.remove("playing");
        document.getElementById("playIcon").innerHTML='<polygon points="5,3 20,12 5,21"/>';
    };

    window.setPrefetch=function(url){prefetchUrl=url;};
})();

// ── Player Controls ──
(function(){
    var audio=document.getElementById("audioPlayer"),
        btn=document.getElementById("playBtn"),icon=document.getElementById("playIcon"),
        bars=document.getElementById("audioBars");
    btn.addEventListener("click",function(){
        if(!audio.paused){
            audio.pause();
        }else{
            if(window.currentTrack&&window.currentTrack.url){
                audio.play().catch(function(){});
            }
        }
    });

    // Update icon based on actual audio state
    audio.addEventListener("play",function(){
        icon.innerHTML='<rect x="4" y="3" width="5" height="18"/><rect x="15" y="3" width="5" height="18"/>';
    });
    audio.addEventListener("pause",function(){
        icon.innerHTML='<polygon points="5,3 20,12 5,21"/>';
    });

    // Previous
    document.getElementById("prevBtn").addEventListener("click",function(){
        if(window.playHistory&&window.playHistory.length){
            var prev=window.playHistory.pop();
            window.playSong(prev.url,prev.name,prev.artist,prev.songId,prev.cover||"");
        }
    });

    // Next
    document.getElementById("nextBtn").addEventListener("click",function(){
        audio.pause(); audio.src="";
        window.currentTrack=null;
        var next=window.queueNext();
        if(next&&next.url){
            window.playSong(next.url,next.name,next.artist,next.songId||0,next.cover||"");
        }else if(window.queueEmpty()){
            window.fetchNext();
        }else{
            bars.classList.remove("playing");
            icon.innerHTML='<polygon points="5,3 20,12 5,21"/>';
        }
    });

    // Stop
    document.getElementById("stopBtn").addEventListener("click",function(){
        if(window.stopMusic)window.stopMusic();
    });

    // 喜欢：持久化到后端
    document.getElementById("likeBtn").addEventListener("click",function(){
        var lb=this;
        var ct=window.currentTrack;
        if(!ct||!ct.url)return;
        if(lb.classList.contains("liked")){
            lb.classList.remove("liked");
            fetch("/api/unlike",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({song_id:ct.songId})}).catch(function(){});
        }else{
            lb.classList.add("liked");
            fetch("/api/like",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({song_name:ct.name,artist:ct.artist,song_id:ct.songId})}).catch(function(){});
        }
    });

    // 隐藏/跳过：跳过当前曲目并加入黑名单
    document.getElementById("hideBtn").addEventListener("click",function(){
        var ct=window.currentTrack;
        if(ct&&ct.songId){
            fetch("/api/like",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({song_name:ct.name,artist:ct.artist,song_id:ct.songId,hide:true})}).catch(function(){});
        }
        window.currentTrack=null;
        var next=window.queueNext();
        if(next&&next.url){
            window.playSong(next.url,next.name,next.artist,next.songId||0,next.cover||"");
        }else if(window.queueEmpty()){
            window.fetchNext();
        }else{
            audio.pause();audio.currentTime=0;playing=false;bars.classList.remove("playing");
            icon.innerHTML='<polygon points="5,3 20,12 5,21"/>';
        }
    });

    // 收藏：持久化到后端
    document.getElementById("favBtn").addEventListener("click",function(){
        var fb=this;
        var ct=window.currentTrack;
        if(!ct||!ct.url)return;
        if(fb.classList.contains("liked")){
            fb.classList.remove("liked");
            fetch("/api/unlike",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({song_id:ct.songId})}).catch(function(){});
        }else{
            fb.classList.add("liked");
            fetch("/api/like",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({song_name:ct.name,artist:ct.artist,song_id:ct.songId})}).catch(function(){});
        }
    });

    // 同步 playing 状态
    audio.addEventListener("play",function(){playing=true;});
    audio.addEventListener("pause",function(){playing=false;});
})();

// ── Progress ──
(function(){
    var audio=document.getElementById("audioPlayer"),
        track=document.getElementById("progressTrack"),
        fill=document.getElementById("progressFill"),
        cur=document.getElementById("currentTime"),
        dur=document.getElementById("duration");
    audio.addEventListener("timeupdate",function(){
        if(!audio.duration)return;
        var pct=(audio.currentTime/audio.duration*100)+"%";
        fill.style.width=pct;
        cur.textContent=fmt(audio.currentTime);
        dur.textContent=fmt(audio.duration);
        // sync FM progress bar
        var fmFill=document.getElementById("fmProgressFill");
        var fmTime=document.getElementById("fmTimeDisplay");
        if(fmFill)fmFill.style.width=pct;
        if(fmTime)fmTime.textContent=fmt(audio.currentTime)+" / "+fmt(audio.duration);
    });
    audio.addEventListener("loadedmetadata",function(){dur.textContent=fmt(audio.duration);});
    track.addEventListener("click",function(e){
        if(!audio.duration)return;
        var rect=track.getBoundingClientRect();
        var x=e.clientX-rect.left;
        audio.currentTime=(x/rect.width)*audio.duration;
    });
    function fmt(s){var m=Math.floor(s/60),sec=Math.floor(s%60);return m+":"+("0"+sec).slice(-2);}
})();

// ── WS /stream Chat ──
(function(){
    var input=document.getElementById("chatInput"),send=document.getElementById("chatSend"),
        list=document.getElementById("chatList"),ws=null,reconnectTimer=null,
        sendTime=0,thinkingEl=null;
    window.wsConnected=false;window.lastLatency=0;

    function setStatus(online){
        var dot=document.getElementById("statusDot");
        var state=document.getElementById("statusState");
        if(online){
            dot.className="status-dot online";
            state.className="status-state online";
            state.textContent="LIVE";
        }else{
            dot.className="status-dot offline";
            state.className="status-state offline";
            state.textContent="OFFLINE";
        }
    }

    function connect(){
        if(ws&&ws.readyState===WebSocket.OPEN)return;
        var proto=location.protocol==="https:"?"wss":"ws";
        ws=new WebSocket(proto+"://"+location.host+"/stream");
        ws.onopen=function(){
            window.wsConnected=true;setStatus(true);
            // let Claudio speak after a brief pause
            setTimeout(function(){
                sendTime=Date.now();
                showThinking();
                ws.send(JSON.stringify({message:"",greet:true}));
            },600);
        };
        ws.onmessage=function(e){
            try{
                var data=JSON.parse(e.data);
                var elapsed=Date.now()-sendTime;
                window.lastLatency=elapsed;
                hideThinking();
                typeReply(data.reply||"",elapsed);
                console.log("[ws] received:",data.action,"songs:",data.songs?data.songs.length:0,"addMode:",_lastWasAdd);
                if(data.action==="play"){
                    var addMode=_lastWasAdd; _lastWasAdd=false;
                    console.log("[ws] playSong for first song, addMode:",addMode);
                    // Single song
                    if(data.song&&data.song.url){
                        if(addMode){
                            window.queueAdd(data.song.name,data.song.artist,data.song.url,data.song.id||0,data.song.cover||"");
                        }else{
                            window.playSong(data.song.url,data.song.name,data.song.artist,data.song.id||0,data.song.cover||"");
                        }
                    }
                    // Multiple songs
                    if(data.songs&&data.songs.length){
                        data.songs.forEach(function(s,i){
                            if(!addMode&&i===0&&s.url){
                                window.playSong(s.url,s.name,s.artist,s.id||0,s.cover||"");
                            }else if(s.url){
                                window.queueAdd(s.name,s.artist,s.url,s.id||0,s.cover||"");
                            }
                        });
                    }
                }
            }catch(err){console.error("[ws] parse error",err);}
        };
        ws.onclose=function(){ws=null;window.wsConnected=false;setStatus(false);reconnectTimer=setTimeout(connect,5000);};
        ws.onerror=function(){ws&&ws.close();};
    }

    function showThinking(){
        if(thinkingEl)return;
        thinkingEl=document.createElement("div");thinkingEl.className="msg ai";
        var now=new Date(),time=("0"+now.getHours()).slice(-2)+":"+("0"+now.getMinutes()).slice(-2);
        thinkingEl.innerHTML='<div class="msg-avatar"><img src="/static/ryan.png" alt="C"></div>'
            +'<div class="msg-body"><div class="msg-meta"><span>CLAUDIO</span><span class="msg-time">'+time+'</span></div>'
            +'<div class="msg-bubble thinking-dots"><span>.</span><span>.</span><span>.</span></div></div>';
        list.appendChild(thinkingEl);list.scrollTop=list.scrollHeight;
    }
    function hideThinking(){
        if(thinkingEl){thinkingEl.remove();thinkingEl=null;}
    }

    function typeReply(text,elapsed){
        if(!text)return;
        var m=document.createElement("div");m.className="msg ai";
        var now=new Date(),time=("0"+now.getHours()).slice(-2)+":"+("0"+now.getMinutes()).slice(-2);
        m.innerHTML='<div class="msg-avatar"><img src="/static/ryan.png" alt="C"></div>'
            +'<div class="msg-body"><div class="msg-meta"><span>CLAUDIO</span><span class="msg-time">'+time+'</span></div>'
            +'<div class="msg-bubble"></div></div>';
        list.appendChild(m);
        var bubble=m.querySelector(".msg-bubble");
        var i=0;
        var speed=elapsed>6000?50:elapsed>3000?30:15;
        function tick(){
            if(i<text.length){
                bubble.textContent+=text[i];
                i++;
                list.scrollTop=list.scrollHeight;
                setTimeout(tick,speed);
            }else{
                bubble.innerHTML=text.replace(/\n/g,"<br>");
            }
        }
        tick();
    }

    function addMsg(text,cls,name){
        if(!text)return;
        var m=document.createElement("div");m.className="msg "+cls;
        var now=new Date(),time=("0"+now.getHours()).slice(-2)+":"+("0"+now.getMinutes()).slice(-2);
        var avatarHTML=cls==="user"?'<div class="msg-avatar"><img src="/static/avatar-user.jpg" alt="You"></div>':'<div class="msg-avatar">'+name.charAt(0)+'</div>';
        m.innerHTML=avatarHTML
            +'<div class="msg-body"><div class="msg-meta"><span>'+name.toUpperCase()+'</span><span class="msg-time">'+time+'</span></div>'
            +'<div class="msg-bubble">'+text.replace(/\n/g,"<br>")+'</div></div>';
        if(cls==="user"){ m.classList.add("sending"); }
        list.appendChild(m);list.scrollTop=list.scrollHeight;
        if(cls==="user"){
            setTimeout(function(){ m.classList.remove("sending"); },200);
        }
    }
    window.addMsg=addMsg;
    window.typeReply=typeReply;

    window.addSystemMsg=function(text){
        if(!text)return;
        var m=document.createElement("div");m.className="msg system";
        m.innerHTML='<div class="msg-bubble">'+escHtml(text)+'</div>';
        list.appendChild(m);list.scrollTop=list.scrollHeight;
    };

    function escHtml(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

    function sendMsg(){
        var t=input.value.trim();if(!t)return;
        input.value="";
        window.sendToDJ(t);
    }
    var _lastWasAdd=false;
    window.sendToDJ=function(message){
        if(!message||!ws||ws.readyState!==WebSocket.OPEN)return;
        // Detect "add to queue" intent
        var lower=message.toLowerCase();
        _lastWasAdd=/\b(add|queue|put.*more|throw.*in|append)\b/.test(lower)||/添加|加点|加几首/.test(message);
        addMsg(message,"user","You");
        sendTime=Date.now();
        showThinking();
        ws.send(JSON.stringify({message:message}));
    };
    send.addEventListener("click",sendMsg);
    input.addEventListener("keydown",function(e){if(e.key==="Enter")sendMsg();});
    connect();
})();

// ── Service Worker ── (FM debug: disabled)
// if("serviceWorker" in navigator){
//     navigator.serviceWorker.register("/static/sw.js");
// }

// ── ClickSpark: 按钮点击波纹 ──
(function(){
    document.querySelectorAll('.ctrl-btn, .chat-send').forEach(function(btn){
        btn.addEventListener('click', function(e){
            var ripple=document.createElement('span');
            var rect=btn.getBoundingClientRect();
            var size=Math.max(rect.width,rect.height);
            ripple.style.cssText=
                'position:absolute;border-radius:50%;width:'+size+'px;height:'+size+'px;'+
                'left:'+(e.clientX-rect.left-size/2)+'px;top:'+(e.clientY-rect.top-size/2)+'px;'+
                'background:rgba(255,255,255,.15);transform:scale(0);'+
                'animation:ripple .6s ease-out forwards;pointer-events:none;';
            btn.appendChild(ripple);
            ripple.addEventListener('animationend',function(){ripple.remove();});
        });
    });
})();


// ── FM: pixel audio bar + script display ──
(function(){
    var barCount=283;
    var baseHeights=[]; // 每根柱子的基底波形高度
    var speakTimer=null;
    var speakActive=false;

    // 生成密排白线波形
    function buildAudioBar(){
        var container=document.getElementById("fmAudioBar");
        if(!container)return;
        container.innerHTML="";
        // 生成自然波形基底：叠加多条正弦波
        for(var i=0;i<barCount;i++){
            var t=i/barCount;
            var h=Math.sin(t*Math.PI*2.7)*0.35;
            h+=Math.sin(t*Math.PI*5.3+1.2)*0.25;
            h+=Math.sin(t*Math.PI*8.1+2.7)*0.18;
            h+=Math.sin(t*Math.PI*14+4.1)*0.12;
            h+=Math.sin(t*Math.PI*22+0.6)*0.06;
            h=Math.abs(h); // 0~1
            h=35+h*100; // 35~135px (higher floor for short bars)
            baseHeights.push(h);
            var px=document.createElement("div");
            px.className="fm-px";
            px.style.height="2px";
            container.appendChild(px);
        }
    }

    // 语音驱动波形跳动
    function voicePulse(){
        var pxs=document.querySelectorAll(".fm-audio-bar .fm-px");
        if(!pxs.length)return;
        var amp=speakActive?0.8+Math.random()*0.3:0.05;
        for(var i=0;i<pxs.length;i++){
            var base=baseHeights[i]||3;
            var jitter=1+(Math.random()-0.5)*0.4;
            var h=Math.max(2,base*amp*jitter);
            pxs[i].style.height=h+"px";
        }
    }

    function startSpeakLoop(){
        if(speakTimer)return;
        speakActive=true;
        function pulse(){
            if(!speakActive){speakTimer=null;return;}
            voicePulse();
            speakTimer=setTimeout(pulse,100+Math.random()*150);
        }
        pulse();
    }

    function stopSpeakLoop(){
        speakActive=false;
        if(speakTimer){clearTimeout(speakTimer);speakTimer=null;}
        // 最后一次静默更新
        setTimeout(function(){
            var pxs=document.querySelectorAll(".fm-audio-bar .fm-px");
            if(!pxs.length)return;
            for(var i=0;i<pxs.length;i++){
                pxs[i].style.height="2px";
            }
        },200);
    }

    window.speakFm=function(active){
        if(active)startSpeakLoop();
        else stopSpeakLoop();
    };

    // ── Transcript rendering ──
    var transcriptEl=document.getElementById("fmTranscript");
    var fmLines=[],fmActiveLine=-1;

    function renderTranscript(){
        if(!transcriptEl)return;
        var h="";
        for(var i=0;i<fmLines.length;i++){
            var L=fmLines[i];
            var activeCls=i===fmActiveLine?" active":"";
            h+='<div class="fm-line'+activeCls+'" id="fmLine'+i+'">';
            h+='<span class="fm-timestamp">'+escHtml(L.time||"")+'</span>';
            h+='<div class="fm-text-wrap">';
            h+='<p class="fm-text-en">'+escHtml(L.en||"")+'</p>';
            h+='<p class="fm-text-zh">'+escHtml(L.zh||"")+'</p>';
            h+='</div></div>';
        }
        transcriptEl.innerHTML=h;
    }
    function escHtml(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

    window.setFmSong=function(name){
        var el=document.getElementById("fmEpSong");
        if(el)el.textContent=name||"—";
    };

    window.loadFmTranscript=function(lines){
        fmLines=lines||[]; fmActiveLine=-1;
        renderTranscript();
    };

    window.highlightFmLine=function(idx){
        if(idx===fmActiveLine)return;
        if(fmActiveLine>=0){
            var old=document.getElementById("fmLine"+fmActiveLine);
            if(old)old.classList.remove("active");
        }
        fmActiveLine=idx;
        var cur=document.getElementById("fmLine"+idx);
        if(cur){
            cur.classList.add("active");
            if(!fmUserScrolledUp){
                cur.scrollIntoView({block:"nearest",behavior:"smooth"});
            }
        }
    };

    window.updateFmTime=function(cur,total){
        var el=document.getElementById("fmTimeDisplay");
        if(!el)return;
        el.textContent=fmtTime(cur)+" / "+fmtTime(total||0);
        // also update progress bar
        var fill=document.getElementById("fmProgressFill");
        if(fill&&total>0)fill.style.width=(cur/total*100)+"%";
    };
    function fmtTime(sec){
        var m=Math.floor(sec/60),s=Math.floor(sec%60);
        return m+":"+("0"+s).slice(-2);
    }

    // ── FM Radio Loop (typewriter) ──
    var fmOn=false, fmFetching=false;
    var fmPendingLines=[];   // lines not yet added to DOM
    var fmTypingLine=null;   // current DOM line being typed
    var fmTypeTimer=null;    // word-by-word timer
    var fmNextTimer=null;    // delay before next line
    var fmLineCount=0;       // total lines added so far

    var fmUserScrolledUp=false;
    if(transcriptEl){
        transcriptEl.addEventListener("scroll",function(){
            var atBottom=transcriptEl.scrollTop+transcriptEl.clientHeight>=transcriptEl.scrollHeight-50;
            fmUserScrolledUp=!atBottom;
        });
    }
    function fmIsAtBottom(){
        if(!transcriptEl)return false;
        return transcriptEl.scrollTop+transcriptEl.clientHeight>=transcriptEl.scrollHeight-50;
    }
    function fmScrollToBottom(force){
        if(!transcriptEl)return;
        if(!force&&fmUserScrolledUp)return;
        // use requestAnimationFrame to ensure DOM has updated
        requestAnimationFrame(function(){
            transcriptEl.scrollTop=transcriptEl.scrollHeight;
            fmUserScrolledUp=false;
        });
    }

    function fmAppendLine(L){
        if(!transcriptEl)return;
        var idx=fmLineCount++;
        var div=document.createElement("div");
        div.className="fm-line entering";
        div.id="fmLine"+idx;
        div.innerHTML=
            '<span class="fm-timestamp">'+escHtml(L.time||"")+'</span>'+
            '<div class="fm-text-wrap">'+
            '<p class="fm-text-en"></p>'+
            '<p class="fm-text-zh"></p>'+
            '</div>';
        transcriptEl.appendChild(div);
        requestAnimationFrame(function(){div.classList.remove("entering");});
        // dim previous lines
        var lines=transcriptEl.querySelectorAll(".fm-line");
        for(var i=0;i<lines.length-1;i++)lines[i].classList.add("dim");
        // auto-scroll unless user scrolled up
        requestAnimationFrame(function(){
            requestAnimationFrame(function(){
                if(!fmUserScrolledUp)fmScrollToBottom();
            });
        });
        return {
            el:div,
            enWords:(L.en||"").split(/\s+/),
            zhWords:(L.zh||"").split(/\s+/),
            enIdx:0, zhIdx:0,
            done:false
        };
    }

    function fmBuildHTML(words,idx){
        // idx ignored for now — green word-hl will be re-added later synced with TTS audio
        if(!words.length)return "";
        return words.map(escHtml).join(" ");
    }

    function fmTypeWord(){
        if(!fmOn||!fmTypingLine)return;
        var T=fmTypingLine;
        var enEl=T.el.querySelector(".fm-text-en");
        var zhEl=T.el.querySelector(".fm-text-zh");
        if(T.enIdx<T.enWords.length){
            T.enIdx++;
            enEl.innerHTML=fmBuildHTML(T.enWords,T.enIdx-1);
            if(T.zhIdx<T.zhWords.length){
                T.zhIdx++;
                zhEl.innerHTML=fmBuildHTML(T.zhWords,T.zhIdx-1);
            }
            fmTypeTimer=setTimeout(fmTypeWord,100+Math.random()*60);
            window.speakFm(true);
            if(!fmUserScrolledUp)requestAnimationFrame(fmScrollToBottom);
        }else{
            if(T.zhIdx<T.zhWords.length){
                T.zhIdx++;
                enEl.innerHTML=fmBuildHTML(T.enWords,-1);
                zhEl.innerHTML=fmBuildHTML(T.zhWords,T.zhIdx-1);
                fmTypeTimer=setTimeout(fmTypeWord,60+Math.random()*40);
                if(!fmUserScrolledUp)requestAnimationFrame(fmScrollToBottom);
            }else{
                T.done=true;
                enEl.innerHTML=fmBuildHTML(T.enWords,-1);
                zhEl.innerHTML=fmBuildHTML(T.zhWords,-1);
                fmTypingLine=null;
                window.speakFm(false);
                // If audio already ended (or this is non-audio intro line), advance
                if(!fmSpeaking)fmAdvance();
            }
        }
    }

    // ── TTS 朗读（Web Audio API，零缓存）──
    var fmSpeaking=false, fmAudioCtx=null, fmCurrentIdx=-1;

    function fmDebug(msg){
        console.log("[fm] "+msg);
    }

    var fmPreBufs={}; // pre-fetched {buf, boundaries} by index

    function fmPreFetch(idx, text){
        text=(text||"").trim();
        if(!text||fmPreBufs[idx])return;
        fmPreBufs[idx]="loading";
        var url="/api/tts?t="+encodeURIComponent(text)+"&_="+Date.now();
        fetch(url).then(function(r){
            if(!r.ok)throw new Error("http "+r.status);
            var boundaries=null;
            try{boundaries=JSON.parse(r.headers.get("X-Word-Boundaries"));}catch(e){}
            return r.arrayBuffer().then(function(buf){return {buf:buf, boundaries:boundaries};});
        })
        .then(function(data){if(!fmAudioCtx)throw new Error("no ctx");return fmAudioCtx.decodeAudioData(data.buf).then(function(audioBuf){return {buf:audioBuf, boundaries:data.boundaries};});})
        .then(function(result){fmPreBufs[idx]=result;fmDebug("✅ pre #"+idx+" ready "+result.buf.duration.toFixed(1)+"s words="+(result.boundaries?result.boundaries.length:0));})
        .catch(function(e){delete fmPreBufs[idx];fmDebug("pre err #"+idx+": "+e.message);});
    }

    var _fmSavedVol=null, _fmDuckTimer=null;

    function _fmFadeVol(target, ms){
        clearInterval(_fmDuckTimer);
        var ap=document.getElementById("audioPlayer");
        var gv=window.musicGain?window.musicGain.gain.value:0;
        var av=ap?ap.volume:0;
        var cur=(gv>0.001)?gv:((av>0.001)?av:target);
        var steps=Math.round(ms/40), step=(target-cur)/steps, i=0;
        _fmDuckTimer=setInterval(function(){
            i++; var v=cur+step*i;
            if(i>=steps){v=target;clearInterval(_fmDuckTimer);}
            if(window.musicGain)window.musicGain.gain.value=v;
            if(ap)ap.volume=v;
        },40);
    }

    function _fmLowerMusic(){
        clearInterval(_fmDuckTimer);
        var ap=document.getElementById("audioPlayer");
        var cur=window.musicGain?window.musicGain.gain.value:(ap?ap.volume:0.3);
        if(cur>0.02) _fmSavedVol=cur;
        var target=Math.max(0.05, (_fmSavedVol||0.6)*0.3);
        _fmFadeVol(target, 600);
    }
    function _fmRestoreMusic(){
        if(_fmSavedVol===null)return;
        var t=_fmSavedVol; _fmSavedVol=null;
        _fmFadeVol(t, 600);
    }

    function fmSpeakLine(idx, text, audioBuf){
        text=(text||"").trim();
        if(!text){fmDebug("skip empty #"+idx); fmAdvance();return;}
        fmCurrentIdx=idx;
        fmClearWordHL();
        window.highlightFmLine(idx);
        fmSpeaking=true;
        updateFmStatusBar();
        function highlightSpan(spans, wi){
            if(wi===fmHlWord)return;
            if(fmHlWord>=0&&fmHlWord<spans.length)spans[fmHlWord].classList.remove("fm-word-hl");
            if(wi>=0&&wi<spans.length)spans[wi].classList.add("fm-word-hl");
            fmHlWord=wi;
        }
        // The highlight reads the audio clock every frame instead of chaining
        // setTimeouts. A timeout lands a few ms late each time and the error
        // compounds word by word, which is why the green word drifted further
        // and further behind the voice down a line. Sampling currentTime means
        // a slow frame can only delay an update, never desync it.
        function startWordHL(buf, boundaries, t0){
            var line=document.getElementById("fmLine"+idx);
            if(!line)return;
            var enEl=line.querySelector(".fm-text-en");
            if(!enEl)return;
            var spans=enEl.querySelectorAll("span");
            var n=spans.length;
            if(n<2)return;

            var times=[], i, acc;
            if(boundaries&&boundaries.length===n){
                // exact per-word starts from the TTS service
                for(i=0;i<n;i++)times.push(boundaries[i].offset/1e7); // 100ns ticks -> seconds
            }else{
                // No usable per-word timing (or a different tokenisation than
                // the service used) — spread the clip by word length, still
                // resolved against the audio clock rather than a timer chain.
                var totalChars=0;
                for(i=0;i<n;i++)totalChars+=(spans[i].textContent||"").length||1;
                acc=0;
                for(i=0;i<n;i++){
                    times.push(acc);
                    acc+=(((spans[i].textContent||"").length||1)/totalChars)*buf.duration;
                }
            }

            fmStopWordHL();
            function tick(){
                if(!fmAudioCtx){fmStopWordHL();return;}
                // wi starts at -1 so the leading silence before the first word
                // lights nothing, rather than lighting word 0 early
                var t=fmAudioCtx.currentTime-t0, wi=-1;
                for(var k=0;k<times.length;k++){if(t>=times[k])wi=k;else break;}
                highlightSpan(spans,wi);
                fmHlRAF=requestAnimationFrame(tick);
            }
            tick();
        }
        function playBuf(buf,label,boundaries){
            var src=fmAudioCtx.createBufferSource();
            src.buffer=buf;
            // TTS volume: 80%
            src.connect(fmAudioCtx.destination);
            src.onended=function(){fmClearWordHL();fmSpeaking=false;updateFmStatusBar();fmAdvance();};
            var t0=fmAudioCtx.currentTime; // reference for word-highlight timing
            src.start(0);
            startWordHL(buf,boundaries,t0);
            fmDebug(label);
        }
        if(audioBuf){
            playBuf(audioBuf.buf||audioBuf,"⚡ #"+idx+" "+(audioBuf.buf||audioBuf).duration.toFixed(1)+"s",audioBuf.boundaries);
        }else{
            if(fmPreBufs[idx]&&fmPreBufs[idx]!=="loading"){
                var pb=fmPreBufs[idx];
                playBuf(pb.buf,"⚡ #"+idx+" "+pb.buf.duration.toFixed(1)+"s",pb.boundaries);
                delete fmPreBufs[idx];
                return;
            }
            var waited=0;
            function waitForPre(){
                if(fmPreBufs[idx]&&fmPreBufs[idx]!=="loading"){
                    var pb2=fmPreBufs[idx];
                    playBuf(pb2.buf,"⚡ #"+idx+" (waited "+waited+"ms)",pb2.boundaries);
                    delete fmPreBufs[idx];
                }else if(waited<3000){
                    waited+=150;
                    setTimeout(waitForPre,150);
                }else{
                    fmDebug("🔊 fallback #"+idx);
                    var url2="/api/tts?t="+encodeURIComponent(text)+"&_="+Date.now();
                    var fbB=null;
                    fetch(url2).then(function(r){
                        if(!r.ok)throw new Error("http "+r.status);
                        try{fbB=JSON.parse(r.headers.get("X-Word-Boundaries"));}catch(e){}
                        return r.arrayBuffer();
                    })
                    .then(function(buf2){if(!fmAudioCtx)throw new Error("no ctx");return fmAudioCtx.decodeAudioData(buf2);})
                    .then(function(audioBuf2){playBuf(audioBuf2,"▶ #"+idx+" "+audioBuf2.duration.toFixed(1)+"s",fbB);})
                    .catch(function(e){fmDebug("err #"+idx+": "+e.message);fmSpeaking=false;updateFmStatusBar();setTimeout(fmAdvance,500);});
                }
            }
            waitForPre();
        }
    }

    function fmTypeLine(div, enWords, zhWords, callback){
        var enEl=div.querySelector(".fm-text-en");
        var zhEl=div.querySelector(".fm-text-zh");
        // full English text with spans for word-level highlighting
        var parts=[]; for(var w=0;w<enWords.length;w++)parts.push("<span>"+escHtml(enWords[w])+"</span>");
        enEl.innerHTML=parts.join(" ");
        // zh typewriter
        var zi=0;
        function tickZh(){
            if(zi<zhWords.length){zhEl.textContent=zhWords.slice(0,zi+1).join("");zi++;setTimeout(tickZh,60+Math.random()*40);}
            else{if(callback)callback();}
        }
        tickZh();
    }

    var fmHlRAF=null;   // requestAnimationFrame handle for the word highlight
    var fmHlWord=-1;    // index of the span currently lit, -1 when none
    function fmStopWordHL(){
        if(fmHlRAF){cancelAnimationFrame(fmHlRAF);fmHlRAF=null;}
        fmHlWord=-1;
    }
    function fmClearWordHL(){
        fmStopWordHL();
        if(transcriptEl){var hls=transcriptEl.querySelectorAll(".fm-word-hl");for(var i=0;i<hls.length;i++)hls[i].classList.remove("fm-word-hl");}
    }

    var fmRevealed=0; // how many lines revealed in DOM
    var fmAllLines=[]; // all line data indexed by global idx

    function fmRevealLine(idx){
        var L=fmAllLines[idx];
        if(!L||!transcriptEl)return;
        var div=document.createElement("div");
        div.className="fm-line entering dim"; // dim immediately
        div.id="fmLine"+idx;
        div.innerHTML='<span class="fm-timestamp">'+(L.time||"")+'</span><div class="fm-text-wrap"><p class="fm-text-en"></p><p class="fm-text-zh"></p></div>';
        transcriptEl.appendChild(div);
        requestAnimationFrame(function(){div.classList.remove("entering");});
        // trim before splitting: stray leading/trailing whitespace would
        // otherwise yield empty spans, and the span count has to line up
        // exactly with the word boundaries the TTS worker reports.
        var enWords=(L.en||"").trim().split(/\s+/);
        var zhWords=(L.zh||"").split(/\s+/);
        fmTypeLine(div, enWords, zhWords);
    }

    function fmRevealLines(count){
        var canReveal=fmAllLines.length - fmRevealed;
        var n=Math.min(count, canReveal);
        if(n<=0)return;
        function next(i){
            if(i>=n||!fmOn)return;
            var idx=fmRevealed;
            fmRevealLine(idx);
            fmRevealed++;
            fmScrollToBottom();
            setTimeout(function(){next(i+1);}, 800+Math.random()*400);
        }
        next(0);
    }

    function fmAdvance(){
        if(!fmOn||fmPaused||fmSpeaking)return;
        if(fmPendingLines.length>0){
            var L=fmPendingLines.shift();
            var idx=fmLineCount;
            fmLineCount++;
            if(idx>=fmRevealed){
                fmRevealLine(idx);
                fmRevealed=idx+1;
            }
            if(transcriptEl){
                var allLines=transcriptEl.querySelectorAll(".fm-line");
                for(var i=0;i<allLines.length;i++)allLines[i].classList.add("dim");
            }
            // reveal only 1 line ahead, slower
            fmRevealLines(1);
            var usePre=null;
            if(fmPreBufs[idx]&&fmPreBufs[idx]!=="loading"){usePre=fmPreBufs[idx];delete fmPreBufs[idx];}
            fmSpeakLine(idx,(L.en||"").trim(),usePre);
            for(var j=0;j<2&&j<fmPendingLines.length;j++){
                fmPreFetch(fmLineCount+j,(fmPendingLines[j].en||"").trim());
            }
            if(fmPendingLines.length<4&&!fmFetching)fmFetchNext();
        }else{
            fmFetchNext();
        }
    }

    function fmShowNextLine(){
        fmAdvance();
    }

    function fmFetchNext(){
        if(fmFetching)return;
        fmFetching=true;
        var ct=window.currentTrack;
        var songParam=ct&&ct.name?(ct.artist||"")+" - "+ct.name:"";
        fetch("/api/fm/script?t="+Date.now()+"&n="+fmLineCount+"&song="+encodeURIComponent(songParam)).then(function(r){return r.json();}).then(function(d){
            fmFetching=false;
            if(!fmOn)return;
            if(fmLineCount<=1){
                if(d.title){var t=document.getElementById("fmEpTitle");if(t)t.textContent=d.title;}
                if(d.subtitle){var s=document.getElementById("fmEpSub");if(s)s.textContent=d.subtitle;}
                var intro=document.getElementById("fmLine0");
                if(intro)intro.remove();
                fmLineCount=0;
            }
            if(d.song){var sg=document.getElementById("fmEpSong");if(sg)sg.textContent=d.song;}
            if(d.song_info&&d.song_info.url){window.playSong(d.song_info.url,d.song_info.name,d.song_info.artist,d.song_info.id,d.song_info.cover||"");}
            // store in allLines + push to pending
            var sec=fmLineCount*5;
            (d.lines||[]).forEach(function(L){
                L.time=fmtTime(sec);
                sec+=Math.max(4,Math.min(10,(L.en||"").split(/\s+/).length*0.7));
                fmAllLines.push(L);
                fmPendingLines.push(L);
            });
            fmDebug("script ready, "+d.lines.length+" lines");
            // pre-fetch TTS for first 3 lines
            for(var j=0;j<3&&j<fmPendingLines.length;j++){
                fmPreFetch(fmLineCount+j,(fmPendingLines[j].en||"").trim());
            }
            // render first 2 lines
            fmRevealLines(2);
            // kick off when first TTS is ready
            function waitFirst(){
                var b=fmPreBufs[fmLineCount];
                if(b&&b!=="loading"){
                    fmDebug("first ready, start");
                    fmAdvance();
                }else if(fmOn){
                    setTimeout(waitFirst,200);
                }
            }
            waitFirst();
        }).catch(function(){
            fmFetching=false;
            if(fmOn)setTimeout(fmFetchNext,3000);
        });
    }

    function fmClearAll(){
        clearInterval(_fmDuckTimer);
        fmTypingLine=null;
        fmPendingLines=[];
        fmLineCount=0;
        fmCurrentIdx=-1;
        fmPreBufs={};
        fmRevealed=0;
        fmAllLines=[];
        if(fmAudioCtx){try{fmAudioCtx.close();}catch(e){}fmAudioCtx=null;}
        fmSpeaking=false;
        if(transcriptEl)transcriptEl.innerHTML="";
    }

    var fmPaused=false;

    var _fmDotsTimer=null, _fmDotsFrame=0;
    function fmtDotsAnim(){
        var txt=document.getElementById("fmStatusText");
        if(!txt)return;
        var frames=[".","..","..."];
        txt.textContent="Speaking"+frames[_fmDotsFrame];
        _fmDotsFrame=(_fmDotsFrame+1)%3;
    }
    function updateFmStatusBar(){
        var dot=document.getElementById("fmStatusDot");
        var txt=document.getElementById("fmStatusText");
        if(!dot||!txt)return;
        if(fmOn && !fmPaused && fmSpeaking){
            dot.classList.add("lit"); txt.classList.remove("paused");
            if(!_fmDotsTimer){
                _fmDotsFrame=0;
                fmtDotsAnim();
                _fmDotsTimer=setInterval(fmtDotsAnim,500);
            }
        }else{
            dot.classList.remove("lit"); txt.textContent="Pause"; txt.classList.add("paused");
            if(_fmDotsTimer){clearInterval(_fmDotsTimer);_fmDotsTimer=null;_fmDotsFrame=0;}
        }
    }

    function fmStart(){
        fmClearAll();
        fmPaused=false;
        fmOn=true;
        fmSpeaking=false;
        fmUserScrolledUp=false;
        _fmSavedVol=null;
        updateFmStatusBar();
        fmDebug("START");
        _fmLowerMusic();
        if(!fmAudioCtx){try{fmAudioCtx=new(window.AudioContext||window.webkitAudioContext)();}catch(e){fmAudioCtx=null;}}
        if(fmAudioCtx&&fmAudioCtx.state==="suspended"){fmAudioCtx.resume();}
        // unlock <audio> element via user click
        var ap2=document.getElementById("audioPlayer");
        if(ap2){ap2.play().catch(function(){});}
        var btn=document.getElementById("fmPlayBtn");
        if(btn)btn.classList.add("playing");
        window.speakFm(true);
        // 显示开场白（打字机效果）
        if(transcriptEl){
            var introDiv=document.createElement("div");
            introDiv.className="fm-line entering";
            introDiv.id="fmLine0";
            introDiv.innerHTML='<span class="fm-timestamp"></span><div class="fm-text-wrap"><p class="fm-text-en"></p><p class="fm-text-zh"></p></div>';
            transcriptEl.appendChild(introDiv);
            requestAnimationFrame(function(){introDiv.classList.remove("entering");});
            fmTypeLine(introDiv, ["Claudio","is","preparing","your","radio..."], ["Claudio","正在为你准备电台节目……"]);
        }
        fmLineCount=1;
        // fetch background music
        window.fetchNext();
        fmFetchNext();
    }

    function fmPause(){
        if(!fmOn||fmPaused)return;
        fmPaused=true;
        _fmRestoreMusic();
        if(fmAudioCtx&&fmAudioCtx.state==="running"){try{fmAudioCtx.suspend();}catch(e){}}
        var btn=document.getElementById("fmPlayBtn");
        if(btn)btn.classList.remove("playing");
        window.speakFm(false);
        updateFmStatusBar();
    }

    function fmResume(){
        if(!fmPaused)return;
        fmPaused=false;
        _fmLowerMusic();
        var btn=document.getElementById("fmPlayBtn");
        if(btn)btn.classList.add("playing");
        window.speakFm(true);
        if(fmAudioCtx&&fmAudioCtx.state==="suspended"){try{fmAudioCtx.resume();}catch(e){}}
        if(!fmSpeaking)fmAdvance();
        updateFmStatusBar();
    }

    function fmStop(){
        fmOn=false; fmPaused=false;
        fmSpeaking=false;
        _fmRestoreMusic();
        if(fmAudioCtx){try{fmAudioCtx.close();}catch(e){}fmAudioCtx=null;}
        var btn=document.getElementById("fmPlayBtn");
        if(btn)btn.classList.remove("playing");
        window.speakFm(false);
        fmFetching=false;
        updateFmStatusBar();
    }

    // ── FM play button ──
    var fmPlayBtn=document.getElementById("fmPlayBtn");
    if(fmPlayBtn){
        fmPlayBtn.addEventListener("click",function(){
            if(fmPaused)fmResume();
            else if(fmOn)fmPause();
            else fmStart();
        });
    }

    window._fmAutoStart=function(){
        if(!fmOn)fmStart();
    };
    window._fmStop=fmStop;

    buildAudioBar();
    setInterval(function(){
        var ct=window.currentTrack;
        var el=document.getElementById("fmEpSong");
        if(el&&ct&&ct.name){el.textContent=ct.artist?ct.artist+" — "+ct.name:ct.name;}
    },2000);
})();

// unlock audio immediately (URL bar Enter counts as user gesture)
try{document.getElementById("audioPlayer").play().catch(function(){});}catch(e){}
setTimeout(function(){window.fetchNext();},800);
