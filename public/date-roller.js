const calendarDate = new Intl.DateTimeFormat("ko-KR", {
  timeZone:"Asia/Seoul", month:"long", day:"numeric", weekday:"short"
});

const kstDay = new Intl.DateTimeFormat("en-CA", {
  timeZone:"Asia/Seoul", year:"numeric", month:"2-digit", day:"2-digit"
});

export function koreaDateKey(now = new Date()) {
  const parts = Object.fromEntries(kstDay.formatToParts(now).map(({type,value})=>[type,value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function fixtureDateKeys(matches,today) {
  return [...new Set([today,...matches.map(match=>match.startsAt.slice(0,10))])].sort();
}

export function mountDateRoller(container, onChange) {
  const owner = container.ownerDocument;
  const view = owner.defaultView;
  const track = owner.createElement("div");
  track.className = "date-roller-track";
  track.setAttribute("role","slider");
  track.setAttribute("aria-label","경기 날짜");
  track.setAttribute("aria-orientation","horizontal");
  track.setAttribute("aria-valuemin","0");
  container.classList.add("date-roller");
  container.replaceChildren(track);

  let values = [];
  let labels = [];
  let items = [];
  let index = 0;
  let drag;
  let timer;

  function leftFor(pos) {
    return items[pos].offsetLeft - items[0].offsetLeft;
  }

  function aligned(pos, animated = false) {
    if (!items.length) return;
    const smooth = animated && !view.matchMedia("(prefers-reduced-motion: reduce)").matches;
    track.scrollTo({left:leftFor(pos),behavior:smooth ? "smooth" : "auto"});
  }

  function selection(pos, notify) {
    const previous = index;
    index = Math.max(0,Math.min(pos,values.length - 1));
    items[previous]?.classList.remove("is-active");
    items[index]?.classList.add("is-active");
    track.setAttribute("aria-valuenow",String(index));
    track.setAttribute("aria-valuetext",labels[index]);
    if (notify && index !== previous) onChange(values[index]);
  }

  function settle() {
    view.clearTimeout(timer);
    if (drag || !track.clientWidth || items.length < 2) return;
    const step = leftFor(1);
    if (step > 0) selection(Math.round(track.scrollLeft / step),true);
  }

  track.addEventListener("scroll",()=>{
    view.clearTimeout(timer);
    timer = view.setTimeout(settle,130);
  },{passive:true});
  track.addEventListener("scrollend",settle);
  track.addEventListener("keydown",event=>{
    const positions = {ArrowLeft:index - 1,ArrowRight:index + 1,Home:0,End:items.length - 1};
    if (!Object.hasOwn(positions,event.key) || !items.length) return;
    event.preventDefault();
    selection(positions[event.key],true);
    aligned(index,true);
  });

  // Leave touch gestures to native scrolling and support the same movement with a desktop mouse.
  track.addEventListener("pointerdown",event=>{
    if (event.pointerType !== "mouse" || event.button !== 0 || items.length < 2) return;
    drag = {id:event.pointerId,x:event.clientX,left:track.scrollLeft};
    track.classList.add("is-dragging");
    track.setPointerCapture(drag.id);
    track.focus({preventScroll:true});
  });
  track.addEventListener("pointermove",event=>{
    if (drag?.id === event.pointerId) track.scrollLeft = drag.left + drag.x - event.clientX;
  });
  track.addEventListener("lostpointercapture",()=>{
    drag = null;
    track.classList.remove("is-dragging");
    settle();
    aligned(index,true);
  });

  const resize = typeof view.ResizeObserver === "function" ? new view.ResizeObserver(()=>aligned(index)) : null;
  resize?.observe(track);

  return {
    destroy() {
      view.clearTimeout(timer);
      resize?.disconnect();
    },
    update(days, current) {
      const dates = ["",...days];
      if (values.length !== dates.length || dates.some((date,i)=>date !== values[i])) {
        values = dates;
        labels = dates.map(date=>date ? calendarDate.format(new Date(date+"T12:00:00+09:00")) : "전체 날짜");
        items = labels.map(label=>{
          const item = owner.createElement("span");
          item.className = "date-roller-item";
          item.setAttribute("aria-hidden","true");
          item.textContent = label;
          return item;
        });
        track.replaceChildren(...items);
        track.tabIndex = items.length > 1 ? 0 : -1;
        track.setAttribute("aria-valuemax",String(items.length - 1));
        track.setAttribute("aria-disabled",String(items.length === 1));
      }
      selection(values.indexOf(current),false);
      aligned(index);
    }
  };
}
