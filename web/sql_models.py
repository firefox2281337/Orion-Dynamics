def get_contacts_sql(contracts_string):
    query = f"""
    CREATE TEMP TABLE temp_contracts (contract_number VARCHAR);
    INSERT INTO temp_contracts (contract_number) VALUES {contracts_string};
    SELECT
        t1.contract_number,
        t3.strah_master_id AS mdm_id,
        CASE WHEN c.phone_f = 100 THEN c.phone ELSE NULL END AS phone,
        CASE WHEN c.phone_f = 100 THEN c.phone2 ELSE NULL END AS phone2,
        CASE WHEN c.phone_f = 100 THEN c.email ELSE NULL END AS email,
        CASE WHEN c.phone_f = 100 THEN c.email2 ELSE NULL END AS email2,
        CASE WHEN c.phone_f = 100 THEN f.birth ELSE NULL END AS birth,
        s_name,
        f_name,
        m_name
    FROM temp_contracts AS t1
    LEFT JOIN public._ins_contract_by_number AS t2 ON t1.contract_number = t2.contract_number
    LEFT JOIN public._ins_contract AS t3 ON t2.contract_id = t3.contract_id
    LEFT JOIN public._subject_master_fl_contact AS c ON c.subject_master_id = t3.strah_master_id
    LEFT JOIN public._subject_master_fl AS f ON f.subject_master_id = t3.strah_master_id;
    """
    return query



def megahelper_sql(period_start, period_end, where_clause):
    sql_query = f"""
DECLARE @period_start NVARCHAR(8) = '{period_start}',
        @period_end NVARCHAR(8) = '{period_end}';

WITH RegisterKaskoSbor AS (
    SELECT
        p.[номер договора к пролонгации]		as [№ Договора К Пролонгации],
        p.Филиал								as [Филиал ВСК],
        p.[Дата окончания ответственности]		as [Дата окончания страхования],
        p.[Наименование страхователя]			as [ФИО],
        p.[вид]									as [Вид страхования],
        p.[Агент]								as [Ответственный сотрудник Агент],
        p.[канал]								as [Канал],
        p.VIN,
        p.[Холдинг],
        gc.mdm_id,
        d.[Марка],
        d.[Модель],
        p.[Код филиала],
        p.[Год выпуска ТС],
        b.[isContactCenter],
        p.[Точка продаж],
        [Продукт] = c.VidPolicy,
        [Ответственный сотрудник ЦО Филиала] = ee.fio,
        [Прошлый период Страховая премия] = p.[База для пролонгации],
        Объект =
            CASE
                WHEN d.[Марка, модель ТС] = 'Не определена Не определена'
                THEN ISNULL(d.Марка, '') + ' ' + ISNULL(d.Модель, '') + ',Год выпуска-' + d.Год_выпуска
                ELSE d.[Марка, модель ТС] + ',Год выпуска-' + d.Год_выпуска
            END,
        [Год пролонгации] =
            CASE
                WHEN ISNULL(yeOld.cntYears, 0) - 1 >= 3 THEN '3+'
                ELSE CAST(ISNULL(yeOld.cntYears, 0) - 1 AS NVARCHAR(10))
            END
    FROM [Controlling].[dbo].[_prolong_auto_base_new_ad] p WITH(NOLOCK)
    LEFT JOIN [Controlling].dbo._control_dimension_num_dog_obj_auto_ad d WITH(NOLOCK)
        ON p.obj_old = d.object_id
    LEFT JOIN Collected.dbo.PolicyRegistry c WITH(NOLOCK)
        ON p.id_web = c.ID
    LEFT JOIN Controlling.._control_dimension_dog_in_ad dd WITH(NOLOCK)
        ON p.dog_old = dd.dog_In_id
    LEFT JOIN Controlling.._control_dimension_emploe_ad ee WITH(NOLOCK)
        ON dd.emploe_id = ee.EMPLOE_ID
    LEFT JOIN Controlling.dbo._prolong_auto_years yeOld WITH(NOLOCK)
        ON yeOld.dog_in_id = p.dog_old AND yeOld.object_id = p.obj_old
    LEFT JOIN controlling.dbo._agg_creatio_dog_in_id b WITH(NOLOCK)
        ON p.dog_old = b.dog_old
    LEFT JOIN [Controlling].[dbo].[_prolong_auto_base_new_ad]  p2 WITH(NOLOCK)
        ON  p.[номер договора к пролонгации] = p2.[Номер договора к пролонгации]
    LEFT JOIN Controlling.dbo._control_dimension_dog_in_ad dd2 WITH(NOLOCK)
        ON p2.dog_old = dd2.dog_In_id
    LEFT JOIN Controlling.._control_dimension_Strah_ad sss WITH(NOLOCK)
        ON dd2.STRACH_ID=sss.STRACH_ID
    LEFT JOIN Publisher..v_mdd_src_customer_binding cs WITH(NOLOCK)
        ON sss.STRACH_ID = cs.strach_id
    LEFT JOIN Publisher..v_MDD_DBO_CUSTOMER   gc WITH(NOLOCK)
        ON cs.mdm_id   = gc.mdm_id
    WHERE
        {where_clause}
)

SELECT
    [№ Договора К Пролонгации],
    [Вид страхования],
    [Продукт],
    [Дата окончания страхования],
    [Год пролонгации],
    [Филиал ВСК],
    [Код филиала],
    [Канал],
    [Прошлый период Страховая премия],
    [Ответственный сотрудник ЦО Филиала],
    [Ответственный сотрудник Агент],
    [Точка продаж],
    mdm_id,
    [ФИО],
    Объект,
    Марка,
    Модель,
    [Год выпуска ТС],
    VIN,
    [Холдинг],
        [Договор к пролонгации передан в АКЦ] =
        CASE
            WHEN isContactCenter IS NOT NULL AND isContactCenter <> '' THEN 'Да'
            ELSE 'Нет'
        END
FROM RegisterKaskoSbor
OPTION (RECOMPILE, MAXDOP 2);
"""
    return sql_query