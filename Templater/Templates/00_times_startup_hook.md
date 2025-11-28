<%*
  // Production startup hook for frontmatter created/modified/accessed.
  // Wire this as a Templater "Startup template".
  // It registers a workspace listener exactly once.
  await tp.user.templater_times.register_times_hook(tp);
%>
