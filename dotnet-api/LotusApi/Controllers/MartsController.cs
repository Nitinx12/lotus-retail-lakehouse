// thin read only marts controller over the governed dbt tables
using LotusApi.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace LotusApi.Controllers;

[ApiController]
[Route("api/marts")]
public class MartsController : ControllerBase
{
    private readonly LotusGoldContext _db;
    public MartsController(LotusGoldContext db) => _db = db;

    [HttpGet("revenue-by-store-month")]
    public async Task<IActionResult> RevenueByStoreMonth(
        [FromQuery] long? storeId, [FromQuery] string? month)
    {
        var query = _db.RevenueByStoreMonths.AsNoTracking().AsQueryable();
        if (storeId is not null) query = query.Where(r => r.StoreId == storeId);
        if (month is not null) query = query.Where(r => r.Month == month);
        return Ok(await query.ToListAsync());
    }
}
