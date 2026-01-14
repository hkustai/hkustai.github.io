// $(document).ready(function(){
//  $('.s-bg-image').height($(window).height());
// })
//
$(".navbar a").click(function (e) {
  var targetId = $(this).data("value");
  if (!targetId) {
    return; // 没有 data-value，交给默认行为
  }

  var $target = $("#" + targetId);
  if ($target.length === 0) {
    return; // 页面不存在目标元素
  }

  e.preventDefault();

  $("body, html").animate(
    { scrollTop: $target.offset().top - 100 },
    1000
  );
});

