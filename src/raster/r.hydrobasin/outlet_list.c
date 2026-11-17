#include <grass/raster.h>
#include <grass/vector.h>
#include <grass/glocale.h>

#include "global.h"

static struct Cell_head window;

void init_outlet_list(struct outlet_list *ol)
{
    G_get_set_window(&window);

    ol->nalloc = ol->n = 0;
    ol->row = ol->col = NULL;
    ol->id = NULL;
}

void reset_outlet_list(struct outlet_list *ol)
{
    ol->n = 0;
}

void free_outlet_list(struct outlet_list *ol)
{
    if (ol->row)
        free(ol->row);
    if (ol->col)
        free(ol->col);
    if (ol->id)
        free(ol->id);
    init_outlet_list(ol);
}

/* adapted from r.path */
void add_outlet(struct outlet_list *ol, int row, int col, int id)
{
    if (ol->n == ol->nalloc) {
        ol->nalloc += REALLOC_INCREMENT;
        ol->row = realloc(ol->row, sizeof *ol->row * ol->nalloc);
        ol->col = realloc(ol->col, sizeof *ol->col * ol->nalloc);
        ol->id = realloc(ol->id, sizeof *ol->id * ol->nalloc);
        if (!ol->row || !ol->col || !ol->id)
            G_fatal_error(_("Unable to increase outlet list"));
    }
    ol->row[ol->n] = row;
    ol->col[ol->n] = col;
    ol->id[ol->n] = id;
    ol->n++;
}

struct outlet_list *read_outlets(char *outlets_name, char *layer, char *idcol)
{
    struct outlet_list *outlets_l = G_malloc(sizeof *outlets_l);
    struct Map_info Map;
    dbDriver *driver = NULL;
    struct field_info *Fi;
    struct line_pnts *Points;
    struct line_cats *Cats;
    int field;
    int nlines, line;

    if (Vect_open_old2(&Map, outlets_name, "", layer) < 0)
        G_fatal_error(_("Unable to open vector map <%s>"), outlets_name);

    field = Vect_get_field_number(&Map, layer);

    /* avoid database queries for the default cat column; it's expensive */
    if (strcmp(idcol, GV_KEY_COLUMN) != 0) {
        Fi = Vect_get_field(&Map, field);
        if (!(driver = db_start_driver_open_database(
                  Fi->driver, Vect_subst_var(Fi->database, &Map))))
            G_fatal_error("Unable to start db driver");
        if (db_column_Ctype(driver, Fi->table, idcol) != DB_C_TYPE_INT)
            G_fatal_error(
                _("Column <%s> in vector map <%s> must be of integer type"),
                idcol, outlets_name);
    }

    Points = Vect_new_line_struct();
    Cats = Vect_new_cats_struct();
    nlines = Vect_get_num_lines(&Map);
    init_outlet_list(outlets_l);

    for (line = 1; line <= nlines; line++) {
        int ltype, cat, id;
        double row, col;

        G_percent(line, nlines, 1);

        ltype = Vect_read_line(&Map, Points, Cats, line);
        Vect_cat_get(Cats, field, &cat);

        if (ltype != GV_POINT || cat < 0)
            continue;

        row = Rast_northing_to_row(Points->y[0], &window);
        col = Rast_easting_to_col(Points->x[0], &window);

        /* if the outlet is outside the computational region, skip */
        if (row < 0 || row >= window.rows || col < 0 || col >= window.cols) {
            G_warning(_("Skip outlet (cat %d) at (%f, %f) outside the current "
                        "region"),
                      cat, Points->x[0], Points->y[0]);
            continue;
        }

        if (driver) {
            dbValue val;

            if (db_select_value(driver, Fi->table, Fi->key, cat, idcol, &val) <
                0)
                G_fatal_error(
                    _("Unable to read column <%s> in vector map <%s>"), idcol,
                    outlets_name);

            id = db_get_value_int(&val);
        }
        else
            id = cat;

        add_outlet(outlets_l, (int)row, (int)col, id);
    }

    if (driver)
        db_close_database_shutdown_driver(driver);

    Vect_close(&Map);

    return outlets_l;
}
