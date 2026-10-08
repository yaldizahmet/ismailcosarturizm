(function(){
var DB = window.__DB;
function Q(t){
  var rows=(DB[t]||[]).slice(), one=false, lim=null;
  var q={
    select:function(){return q},
    eq:function(c,v){rows=rows.filter(function(r){return r[c]===v});return q},
    neq:function(c,v){rows=rows.filter(function(r){return r[c]!==v});return q},
    in:function(c,a){rows=rows.filter(function(r){return a.indexOf(r[c])>=0});return q},
    gte:function(c,v){rows=rows.filter(function(r){return r[c]>=v});return q},
    order:function(c,o){var d=o&&o.ascending===false?-1:1;rows.sort(function(a,b){return (a[c]>b[c]?1:a[c]<b[c]?-1:0)*d});return q},
    limit:function(n){lim=n;return q},
    single:function(){one=true;return q}, maybeSingle:function(){one=true;return q},
    insert:function(){return Promise.resolve({data:null,error:null})},
    update:function(){return q}, delete:function(){return q},
    then:function(r,j){var d=lim?rows.slice(0,lim):rows;return Promise.resolve({data:one?(d[0]||null):d,error:null}).then(r,j)}
  };return q;}
window.supabase={createClient:function(){return {
  from:Q,
  auth:{getSession:function(){return Promise.resolve({data:{session:null}})},onAuthStateChange:function(){return {data:{subscription:{unsubscribe:function(){}}}}},signInWithPassword:function(){return Promise.resolve({error:{message:'test'}})},signOut:function(){return Promise.resolve({})}},
  storage:{from:function(){return {upload:function(){return Promise.resolve({})},getPublicUrl:function(){return {data:{publicUrl:''}}}}}}
}}};
})();
