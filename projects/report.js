// Count-up for headline figures and fade-in for sections. Both are skipped when reduced motion is preferred.
(function(){
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var sections = document.querySelectorAll('main section, figure');
  if (reduce || !('IntersectionObserver' in window)) return;

  sections.forEach(function(el){ el.classList.add('reveal'); });
  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(e){ if (e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
  }, {rootMargin:'0px 0px -8% 0px'});
  sections.forEach(function(el){ io.observe(el); });

  document.querySelectorAll('[data-count]').forEach(function(el){
    var target = parseFloat(el.getAttribute('data-count'));
    var decimals = (el.getAttribute('data-count').split('.')[1] || '').length;
    var prefix = el.getAttribute('data-prefix') || '', suffix = el.getAttribute('data-suffix') || '';
    var start = null, dur = 1100;
    function fmt(n){ return prefix + n.toLocaleString('en-GB', {minimumFractionDigits:decimals, maximumFractionDigits:decimals}) + suffix; }
    el.textContent = fmt(0);
    function step(t){
      if (!start) start = t;
      var p = Math.min((t - start) / dur, 1), eased = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(target * eased);
      if (p < 1) requestAnimationFrame(step); else el.textContent = fmt(target);
    }
    requestAnimationFrame(step);
  });
})();
