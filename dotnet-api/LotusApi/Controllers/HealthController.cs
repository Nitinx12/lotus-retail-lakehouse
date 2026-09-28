// dependency free liveness probe for the container healthcheck
using Microsoft.AspNetCore.Mvc;

namespace LotusApi.Controllers;

[ApiController]
[Route("api/health")]
public class HealthController : ControllerBase
{
    [HttpGet("live")]
    public IActionResult Live() => Ok(new { status = "ok" });
}
